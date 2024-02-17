"""
core/base.py

Last updated:  2024-02-17

Basic configuration and structural stuff.

=+LICENCE=================================
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

=-LICENCE=================================
"""

import sys, os

if __name__ == "__main__":
    # Enable package import if running module directly
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
else:
    appdir = sys.path[0]
basedir = os.path.dirname(appdir)


def APPDATAPATH(path):
    """Return a path within the school-data folder.
    <path> is a '/'-separated path relative to this folder.
    """
    return os.path.join(basedir, "program-data", *path.split("/"))

### +++++


from configparser import ConfigParser

__REPORT = None

#NO_DATE = "*"  # an unspecified date

### -----

__TRANSLATIONS = ConfigParser()
__TRANSLATIONS.read(APPDATAPATH("Translations.ini"), encoding = "utf-8")


def Tr(module_key):
    tk = __TRANSLATIONS[module_key]

    def __translator(_key, **kargs):
        return tk[_key].replace("¶", "\n").format(**kargs)

    return __translator

#T = Tr("core.base")


def set_reporter(function):
    global __REPORT
    __REPORT = function


def __report(mtype, text):
    """The default reporting function prints to stdout.
    It's effect can be overridden later by calling <set_reporter>.
    """
    if __REPORT:
        __REPORT(mtype, text)
    else:
        print("%s: %s" % (mtype, text), flush=True)


def REPORT_CRITICAL(text):
    __report("CRITICAL", text)
    quit(1)


def REPORT_ERROR(text):
    __report("ERROR", text)


def REPORT_WARNING(text):
    __report("WARNING", text)


def REPORT_INFO(text):
    __report("INFO", text)


def REPORT_OUT(text):
    __report("OUT", text)


def REPORT_DEBUG(text):
    if DEBUG:
        __report("DEBUG", text)

# TODO: configuration/settings file?
# posix: os.path.expanduser('~/.config/WZ')
# win: os.path.expanduser('~\\AppData\\Local\\Programs\\WZ\\config')
# Could use the "winpath" package, but it seems unnecessary!
# Can perhaps also install to the WZ folder on windows?
# Perhaps there can also be a launcher there (see python)?
# On Linux install to .local/(bin, lib, share)? or to ~/bin/WZ?


__DATA = None  # Base folder for school data


def setup(basedir, year = None, debug = False):
    """Initialize data paths, etc.
    <basedir> is the full path to the folder containing the year-data
    folders.
    <datadir> is the folder to be selected (containing the school data
    for the current year).
    """
    global __DATA, DEBUG
    DEBUG = debug
    if year:
        __DATA = year_data_path(year, basedir = basedir)
    else:
        __DATA = os.path.join(basedir, "TESTDATA")


def year_data_path(year, path = "", basedir = None):
    """Return the directory (full path) containing the data for the
    given year.
    """
    return os.path.join(
        basedir or os.path.dirname(__DATA),
        f"DATA-{year}",
        *path.split("/")
    )


def DATAPATH(path, base=""):
    """Return a path within the school-data folder.
    <path> is a '/'-separated path relative to this folder.
    <base> is an optional alternative, '/'-separated base folder
    within the data folder.
    """
    return os.path.join(__DATA, *base.split("/"), *path.split("/"))


def RESOURCEPATH(path):
    """Return a path within the resources folder.
    <path> is a '/'-separated path relative to this folder.
    """
    return os.path.join(__DATA, "RESOURCES", *path.split("/"))


# TODO?:
'''
import tarfile

# tarfile doesn't have the encoding problems some
# filenames have with zipfile.
def archive_testdata():
    # The filter is perhaps a nice idea, but I suspect it is not really of
    # much practical use. If an archive is unpacked by a normal user, its
    # contents will be owned by that user anyway.
    def owner(tf0):
        tf0.uid = 0
        tf0.gid = 0
        tf0.uname = "root"
        tf0.gname = "root"
        return tf0

    with tarfile.open("testdata.tar.gz", "w:gz") as tf:
        for root, directories, files in os.walk("TESTDATA"):
            if os.path.basename(root) == "tmp":
                continue
            for filename in files:
                #tf.add(os.path.join(root, filename), filter = owner)
                tf.add(os.path.join(root, filename))


# To read just one file
# tx = tf.extractfile('TESTDATA/CONFIG')
# tx.read() -> <bytes>
'''
