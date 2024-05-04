"""
core/dates.py - last updated 2024-05-04

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

from core.wzbase import Tr
T = Tr("core.dates")

### +++++

from typing import Optional
from datetime import datetime

ISOTIME = "%Y-%m-%d"    # iso time format for datetime.strptime, etc.

#TODO: The date formatting options of Python's strftime (which uses the C
# library) may be too restrictive. For example, days and months are not
# available (in a platform-independent way) without zero-padding.

### -----


def isodate(date: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date, ISOTIME)
    except ValueError:
        return None


def print_date(date: str, date_format: str) -> str:
    """Convert a date string from the program format (ISO, e.g.
    "2016-12-06") to the format used for output (e.g. "06.12.2016").
    If an invalid date is passed, a <ValueError> is raised.
    """
    d = isodate(date)
    if d is None:
        raise ValueError(T("BAD_DATE", date = date))
    return d.strftime(date_format)


def timestamp():
    """Return a "timestamp", accurate to the minute.
    It can be used for dating files, etc.
    """
    return datetime.datetime.now().strftime(f"{ISOTIME}_%H:%M")
