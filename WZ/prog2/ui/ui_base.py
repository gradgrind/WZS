"""
ui/ui_base.py

Last updated:  2024-03-30

Support stuff for the GUI: application initialization, dialogs, etc.


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

import sys, os, locale, traceback, glob, time

if __name__ == "__main__":
    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import APPDATAPATH

# Import all qt stuff needed by this module AND by other modules, so that
# they can just import from here.
from PySide6.QtWidgets import (     # noqa: F401
    QApplication,
    QWidget,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QVBoxLayout,
    QTextEdit,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsSimpleTextItem,
    QMenu,
)
from PySide6.QtGui import (     # noqa: F401
    QIcon,
    QCursor,
    QColor,
    QFont,
    QBrush,
    QPen,
    QPainter,
    QTransform,
)
from PySide6.QtCore import (   # noqa: F401
    QCoreApplication,
    Qt,
    QObject,
    QSettings,
    QLocale,
    QLibraryInfo,
    QTranslator,
    QDir,
    QEvent,
    QRectF,
    QTimer,
)
#Signal = pyqtSignal
#Slot = pyqtSlot
#from PySide6.QtSql import *
#from PyQt6 import uic
from PySide6.QtUiTools import QUiLoader

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
SETTINGS = QSettings(
    QSettings.Format.IniFormat, QSettings.Scope.UserScope, "MT", "WZ"
)

# This seems to deactivate activate-on-single-click in filedialog
# (presumably elsewhere as well?)
APP.setStyleSheet("QAbstractItemView { activate-on-singleclick: 0; }")

QIcon.setFallbackSearchPaths([APPDATAPATH("icons")])


def run(window):
    window.show()
    sys.exit(APP.exec())


class GuiError(Exception):
    pass


from core.base import Tr, set_reporter, REPORT_CRITICAL
T = Tr("ui.ui_base")

### -----

#TODO: Would it be worth considering a sort of cache of loaded ui files?
# I assume that the space used by a dialog will be available for release by
# the garbage collector after the dialog is closed – as long as the dialog
# is not added as a child to some permanent structure. But I haven't been
# able to confirm this, the memory footprint seems to grow with each new
# dialog call.
# If a cache was used, it would be necessary to fully initialize a dialog
# on entry and not rely on settings in the ui-file which might be changed
# on useage.


def get_ui(
    uipath: str,
    parent: QWidget = None,
    wrapper: object = None
) -> QWidget:
    """A ui-file (qt designer) loader for PySide6.
    The designer file is looked for in the "ui" subdirectory of APPDATAPATH.
    If no parent QWidget is supplied, an unparented widget will be returned.
    If <wrapper> is supplied, signals in the ui-file will be automatically
    connected to "slots" in the given object.
    This can work in Python because the "slots" don't have to be actual
    Qt-slots, a normal Python function is possible.
    """
    loader = QUiLoader()
    datadir = APPDATAPATH("ui")
    loader.setWorkingDirectory(QDir(datadir))
    ui = loader.load(os.path.join(datadir, uipath), parent)
    if not ui:
        REPORT_CRITICAL("Bug in ui_base.get_ui: {loader.errorString()}")
    if wrapper:
        for name in dir(wrapper):
            try:
                pre, sig = name.split("_", 1)
            except ValueError:
                continue
            if pre == "on":
                try:
                    widget, sig = sig.rsplit("_", 1)
                except ValueError:
                    obj = ui
                else:
                    obj = getattr(ui, widget)
                getattr(obj, sig).connect(getattr(wrapper, name))
    return ui


class EventFilter(QObject):
    """Implement an event filter for a given widget.
    """
    def __init__(self, obj: QObject, handler):
        super().__init__()
        self.handler = handler
        obj.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        return self.handler(obj, event)
        #if event.type() == QEvent.Type.KeyPress:
        #    key = event.key()
        #    if key == Qt.Key.Key_Space:
        #        do_something()
        #        return True
        ## otherwise standard event processing
        #return False


class HoverRectItem(QGraphicsRectItem):
    """
    """
    def __init__(self, *args, hover = None, **kargs):
        """<handler> should be a function like
            def hover_handler(graphicsitem: QGraphicsItem, enter: bool):
                print("ENTER:", enter)
        """
        self.handler = hover
        super().__init__(*args, **kargs)
        if hover:
            self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        self.handler(self, True)

    def hoverLeaveEvent(self, event):
        self.handler(self, False)


def get_icon(name):
    ilist = glob.glob(APPDATAPATH(f"icons/{name}.*"))
    return QIcon(ilist[0])


def SHOW_INFO(message):
    QMessageBox.information(
        None, T("INFO"), " " * 100 + "\n" + message.rstrip() + "\n"
    )


def SHOW_WARNING(message):
    QMessageBox.warning(
        None, T("WARNING"), " " * 100 + "\n" + message.rstrip() + "\n"
    )


def SHOW_ERROR(message):
    QMessageBox.critical(
        None, T("ERROR"), " " * 100 + "\n" + message.rstrip() + "\n"
    )


def SHOW_CRITICAL(message):
    QMessageBox.critical(
        None, T("CRITICAL"), " " * 100 + "\n" + message.rstrip() + "\n"
    )
    quit(1)


def SHOW_CONFIRM(question):
    return (
        QMessageBox.question(
            None,
            T("CONFIRMATION"),
            " " * 100 + "\n" + question.rstrip() + "\n",
            buttons=(
                QMessageBox.StandardButton.Ok
                | QMessageBox.StandardButton.Cancel
            ),
            defaultButton=QMessageBox.StandardButton.Ok,
        )
        == QMessageBox.StandardButton.Ok
    )


### File/Folder Dialogs

def OPEN_FILE(filetype, start="", title=None):
    """If <start> is a path (with directories), it will be passed to
    the QFileDialog as start address. Otherwise the last used directory
    or the home folder will be used as starting point.
    """
    if os.path.dirname(start):
        dir0 = start
    else:
        dir0 = SETTINGS.value("LAST_LOAD_DIR") or os.path.expanduser("~")
        if start:
            dir0 = os.path.join(dir0, start)
    fpath = QFileDialog.getOpenFileName(
        None, title or T("FILEOPEN"), dir0, filetype
    )[0]
    if fpath:
        SETTINGS.setValue("LAST_LOAD_DIR", os.path.dirname(fpath))
    return fpath


def GET_FOLDER(start=None, title=None):
    """If no <start> is given, the last used directory
    or the home folder will be used as starting point.
    """
    if start:
        dir0 = start
    else:
        dir0 = SETTINGS.value("LAST_DIR") or os.path.expanduser("~")
    dpath = QFileDialog.getExistingDirectory(
        None,
        title or T("DIROPEN"),
        dir0,
        QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
    )
    if dpath:
        SETTINGS.setValue("LAST_DIR", dpath)
    return dpath


def SAVE_FILE(filetype, start=None, title=None):
    """If <start> is a path (with directories), it will be passed to
    the QFileDialog as start address. Otherwise the last used directory
    or the home folder will be used as starting point.
    """
    if os.path.dirname(start):
        dir0 = start
    else:
        dir0 = SETTINGS.value("LAST_SAVE_DIR") or os.path.expanduser("~")
        if start:
            dir0 = os.path.join(dir0, start)
    fpath = QFileDialog.getSaveFileName(
        None, title or T("FILESAVE"), dir0, filetype
    )[0]
    if fpath:
        SETTINGS.setValue("LAST_SAVE_DIR", os.path.dirname(fpath))
    return fpath


class __Reporter(QDialog):
    colours = {
        "INFO":     "#00a000",
        "WARNING":  "#eb8900",
        "ERROR":    "#d00000",
        "CRITICAL": "#8900ae",
        "OUT":      "#ee00ee",
        "DEBUG":    "#00a4cc",
    }

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(2, 2, 2, 2)
        self.reportview = QTextEdit()
        self.reportview.setReadOnly(True)
        vbox.addWidget(self.reportview)
        # vbox.addWidget(HLine())
        buttonBox = QDialogButtonBox()
        vbox.addWidget(buttonBox)
        self.bt_done = buttonBox.addButton(QDialogButtonBox.StandardButton.Ok)
        self.bt_done.clicked.connect(self.ok)
        self.resize(600, 400)
        self.__active = False

    def ok(self):
        self.__close_pending = True

    def closeEvent(self, e):
        if self.__active:
            self.__close_pending = True
            e.ignore()
        else:
            e.accept()

    def keyPressEvent(self, e):
        if self.__active:
            if e.key() in (Qt.Key_Escape, Qt.Key_Return):
                self.__close_pending = True
        else:
            super().keyPressEvent(e)

    def start(self, task, title=None, **kargs):
        self.setWindowTitle(title or T("Reporter"))
        self.setModal(True)
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.bt_done.setEnabled(False)
        self.show()
        self.__active = True
        self.reportview.clear()
        txt = f'+++ {T("PROCESSING")} ...'
        self.reportview.append(f'<span style="color:#d406e3;">{txt}</span>')
        self.reportview.append('')
        self.errorcount = 0
        self.warningcount = 0
        self.__close_pending = False
        time.sleep(0.01)
        QCoreApplication.processEvents()
        result = task(**kargs)
        txt = f'+++ ... {T("DONE")}'
        self.reportview.append(f'<span style="color:#d406e3;">{txt}</span>')
        if self.errorcount:
            clr = self.colours["ERROR"]
            txt = T("ERRORS", n = self.errorcount)
            self.reportview.append(f'<span style="color:{clr};">{txt}</span>')
        if self.warningcount:
            clr = self.colours["WARNING"]
            txt = T("WARNINGS", n = self.warningcount)
            self.reportview.append(f'<span style="color:{clr};">{txt}</span>')
        self.__active = False
        self.bt_done.setEnabled(True)
        QApplication.restoreOverrideCursor()
        while not self.__close_pending:
            QCoreApplication.processEvents()
            time.sleep(0.01)
        self.hide()
        return result

    def newtext(self, mtype, text):
        try:
            ttype = {
                "CRITICAL": T("CRITICAL"),
                "ERROR": T("ERROR"),
                "WARNING": T("WARNING"),
                "INFO": T("INFO"),
            }[mtype]
        except KeyError:
            ttype = mtype or ""
        text = text or ""
        if mtype == "CRITICAL":
            SHOW_CRITICAL(text)
        elif self.__active:
            if mtype or text:
                if mtype:
                    if mtype == "ERROR":
                        self.errorcount += 1
                    elif mtype == "WARNING":
                        self.warningcount += 1
                    clr = self.colours.get(mtype) or "#800080"
                    t0 = f'<span style="color:{clr};">*** {ttype} ***</span>'
                    self.reportview.append(t0)
                self.reportview.append(text.rstrip() + "\n")
            QCoreApplication.processEvents()
        else:
            if mtype == "ERROR":
                SHOW_ERROR(text)
            elif mtype == "WARNING":
                SHOW_WARNING(text)
            elif mtype == "INFO":
                SHOW_INFO(text)
            elif mtype == "DEBUG":
                SHOW_INFO(f"*** DEBUG ***\n{text}")
            else:
                SHOW_CRITICAL(f"BUG: Bad REPORT type: '{ttype}'\n ... {text}")


__reporter = __Reporter()
set_reporter(__reporter.newtext)
PROCESS = __reporter.start


############### Handle uncaught exceptions ###############
class UncaughtHook(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This registers the <exception_hook> method as hook with
        # the Python interpreter
        sys.excepthook = self.exception_hook

    def exception_hook(self, exc_type, exc_value, exc_traceback):
        """Function handling uncaught exceptions.
        It is triggered each time an uncaught exception occurs.
        """
        log_msg = "{val}\n\n$${emsg}".format(
            val=exc_value,
            emsg="".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            ),
        )
        # Show message
        SHOW_ERROR("*** TRAP ***\n" + log_msg)


# Create a global instance of <UncaughtHook> to register the hook
qt_exception_hook = UncaughtHook()


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.base import REPORT_INFO, REPORT_WARNING, REPORT_ERROR

    def run_me(first="First line"):
        time.sleep(2)
        REPORT_INFO(first)
        time.sleep(2)
        REPORT_WARNING("Second line\n\n")
        time.sleep(2)
        REPORT_ERROR(
            "A much, much longer message, which could be\n"
            "something of a problem. Not least because it contains\n"
            "line-break characters. Let's see what happens!",
        )
        time.sleep(2)

    run_me()
    if SHOW_CONFIRM("Continue?"):
        PROCESS(run_me, "Test function", first="Alternative first line")
