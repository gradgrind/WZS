"""
ui_base.py

Last updated:  2024-07-25

Provide some basic canvas support using the QGraphics framework.


=+LICENCE=============================
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

=-LICENCE========================================
"""

import sys, os, locale
this = sys.path[0]
appdir = os.path.dirname(this)
sys.path[0] = appdir
basedir = os.path.dirname(appdir)

from PySide6.QtWidgets import (     # noqa: F401
    QApplication,
)
from PySide6.QtGui import (     # noqa: F401
    QIcon,
)
from PySide6.QtCore import (     # noqa: F401
    QLocale,
    QLibraryInfo,
    QTranslator,
)

def init_app():
    #__locale = locale.setlocale(locale.LC_ALL, "")
    __locale = locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
    print("LOCALE:", __locale)

    #print("STYLES:", QStyleFactory.keys())
    #QApplication.setStyle('Fusion')
    #QApplication.setStyle('Windows')
    APP = QApplication(sys.argv)

    qlocale = QLocale(__locale)
    QLocale.setDefault(qlocale)
    print("uiLanguages:", qlocale.uiLanguages())
    print("system uiLanguages:", QLocale.uiLanguages(QLocale.system()))

    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    translator = QTranslator(APP)
    if translator.load(qlocale, "qtbase", "_", path):
        APP.installTranslator(translator)
    # ?
    #SETTINGS = QSettings(
    #    QSettings.Format.IniFormat, QSettings.Scope.UserScope, "MT", "WZ"
    #)

    # This seems to deactivate activate-on-single-click in filedialog
    # (presumably elsewhere as well?)
    APP.setStyleSheet("QAbstractItemView { activate-on-singleclick: 0; }")
    QIcon.setFallbackSearchPaths([APPDATAPATH("icons")])


def run():
    sys.exit(qApp.exec())


def APPDATAPATH(path):
    """Return a path within the data folder.
    <path> is a '/'-separated path relative to this folder.
    """
    return os.path.join(basedir, "program-data", *path.split("/"))

