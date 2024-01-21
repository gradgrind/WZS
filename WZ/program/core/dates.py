"""
core/dates.py - last updated 2024-01-21

Manage date-related information.


==============================
Copyright 2024 Michael Towers

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
if __name__ == "__main__":
    # Enable package import if running as module
    import sys

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, "TESTDATA"))

from core.base import Tr
T = Tr("core.dates")

### +++++

from typing import Optional
import datetime

from core.base import REPORT_CRITICAL
from core.basic_data import (
    CONFIG,
    CALENDAR,
    DATAPATH,
    ISOTIME,
    isodate,
)

class DataError(Exception):
    pass

#TODO: The date formatting options of Python's strftime (which uses the C
# library) may be too restrictive. For example, days and months are not
# available (in a platform-independent way) without zero-padding.

### -----


def print_date(date: str, date_format: str = None, trap: bool = True
) -> Optional[str]:
    """Convert a date string from the program format (e.g. "2016-12-06")
    to the format used for output (e.g. "06.12.2016").
    If an invalid date is passed, a <DataError> is raised, unless
    <trap> is false. In that case <None> – an invalid date – is returned.
    """
    d = isodate(date)
    if d is None:
        if trap:
            raise DataError(T("BAD_DATE", date = date))
    else:
        if date_format is None:
            date_format = CONFIG.FORMAT_DATE
        return d.strftime(date_format)
    return None


def today(date_format: str = None) -> str:
    """Get the current date.
    <date_format> is a string defining the output format, in the form
    required by <datetime.datetime.strftime>. If not supplied, iso-format
    (YYYY-MM-DD) will be used.
    """
    today = None
    # Allow "faking" the current date (at least in some respects ...).
    fakepath = DATAPATH("__TODAY__")
    if os.path.isfile(fakepath):
        with open(fakepath, encoding="utf-8") as fh:
            for l in fh.readlines():
                l = l.strip()
                if l and l[0] != "#":
                    today = isodate(l)
                    if today is None:
                        REPORT_CRITICAL(f"Bug: Invalid date in {fakepath}")
                    break
    if today is None:
        today = datetime.date.today()
    if date_format is None:
        date_format = ISOTIME
    return today.strftime(date_format)


def timestamp():
    """Return a "timestamp", accurate to the minute.
    It can be used for dating files, etc.
    """
    return datetime.datetime.now().strftime(f"{ISOTIME}_%H:%M")


def next_year() -> str:
    return str(int(CALENDAR.SCHOOL_YEAR) + 1)


def check_schoolyear(date: str = None):
    """Test whether the given date lies within the schoolyear of the
    currently active calendar.
    If no date is given, use "today".
    Return true/false.
    """
    d1, d2 = CALENDAR.ACCOUNTING_YEAR
    if date is None:
        date = today()
    if isodate(date) is None:
        raise DataError(T("BAD_DATE", date = date))
    return date >= d1 and date <= d2



def migrate_calendar(new_year: str = None
) -> list[tuple[int, str, dict[str, str]]]:
    """Generate a "starter" calendar for the given school-year.
    It simply takes the current calendar and changes anything that
    looks like a year to fit the new year. The result of course still
    needs extensive editing, but it should provide useable initial data.
    If no <new_year> is supplied, use the one following the currently
    active one (from CALENDAR).
    """
    y = int(CALENDAR.SCHOOL_YEAR)
    y0, y1 = CALENDAR.ACCOUNTING_YEAR
    y0 = y0.split('-', 1)[0]
    y1 = y1.split('-', 1)[0]
    dy = 1 if new_year is None else int(new_year) - y
    ny0 = str(int(y0) + dy)
    ny1 = str(int(y1) + dy)
    db = get_database()
    cal = db.table("__CALENDAR__")
    changes = []
    for rec in cal.records:
        ddb = {}
        d1 = rec.DATE1
        if d1:
            d_y, d_md = d1.split('-', 1)
            if d_y == y0:
                ddb["DATE1"] = f"{ny0}-{d_md}"
            elif d_y == y1:
                ddb["DATE1"] = f"{ny1}-{d_md}"
        d2 = rec.DATE2
        if d2:
            d_y, d_md = d2.split('-', 1)
            if d_y == y0:
                ddb["DATE2"] = f"{ny0}-{d_md}"
            elif d_y == y1:
                ddb["DATE2"] = f"{ny1}-{d_md}"
        changes.append((rec.id, rec.KEY, ddb))
    return changes


#################################################################
'''
#TODO ...
def save_calendar(cls, text, fpath=None):
    """Save the given text as a calendar file to the given path.
    If no path is supplied, don't save.
    If the path is '*', save as the current calendar file.
    Some very minimal checks are made.
    Return the (modified) text.
    """
    print("SAVE CALENDAR", fpath)
    cls.check_calendar(_Minion.parse(text))  # check the school year
    header = CONFIG["CALENDAR_HEADER"].format(date=cls.today())
    try:
        text = text.split("#---", 1)[1]
        text = text.lstrip("-")
        text = text.lstrip()
    except:
        pass
    text = header + text
    if fpath:
        if fpath == '*':
            fpath = DATAPATH("CONFIG/Calendar")
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as fh:
            fh.write(text)
    return text

def get_calendar(cls, fpath):
    """Parse the given calendar file (full path):"""
    cal = MINION(fpath)
    cls.check_calendar(cal)
    return cal

def check_calendar(cls, calendar):
    print("\n*** TODO: check_calendar (uses check_schoolyear) ***\n")
    return calendar


    """Check the given calendar object."""
    schoolyear = cls.calendar_year(calendar)
    # Check that the year is reasonable
    y0 = cls.today().split("-", 1)[0]
    try:
        y1 = int(schoolyear)
    except ValueError:
        raise DataError(T("INVALID_SCHOOLYEAR", year = schoolyear))
    if y1 < int(y0) or y1 > int(y0) + 2:
        raise DataError(T("DODGY_SCHOOLYEAR", year = schoolyear))
    for k, v in calendar.items():
        if isinstance(v, list):
            # range of days, check validity
            if k[0] == "~" or (
                cls.check_schoolyear(schoolyear, v[0])
                and cls.check_schoolyear(schoolyear, v[1])
            ):
                continue
        else:
            # single day or year field, check validity
            if "SCHOOLYEAR" in k:
                continue
            if k[0] == "~" or cls.check_schoolyear(schoolyear, v):
                continue
        raise DataError(T("BAD_DATE_CAL", line = "%s: %s" % (k, v)))
    return calendar

def calendar_year(calendar):
    """Return the school-year of the given calendar."""
    try:
        return calendar["LAST_DAY"].split("-", 1)[0]
    except KeyError:
        raise DataError(T("MISSING_LAST_DAY"))
'''


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    db = get_database()

    print("A date:", print_date("2016-04-25"))
    try:
        print("BAD Date:", print_date("2016-02-30"))
    except DataError as e:
        print(" ... trapped:", e)
    print("Today (possibly faked):", today())
    print("Today2 (possibly faked):", today("%x"))
    print("Current school year?:", check_schoolyear())
    print("School year of data:", CALENDAR.SCHOOL_YEAR)
    print("Next year:", next_year())
    print("Timestamp:", timestamp())

    print("\nNew calendar:")
    for l in migrate_calendar():
        print(" $$", l)

    quit(1)

    new_year = Dates.next_year()
    print(
        f"\n\nCalendar for {new_year}:\n"
        + Dates.migrate_calendar(save=False)
    )

    t = Tr("core.base")
    print("§translate1:", t("MISSING_LAST_DAY"))
    print("§translate2:", t("BAD_DATE", date = "2023.12.17"))
