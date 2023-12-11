"""
ui/dialogs/dialog_make_course_tables.py

Last updated:  2023-12-11

Supporting "dialog", for the course editor – allow the export of teacher
and class data, etc., in table form.


=+LICENCE=============================
Copyright 2023 Michael Towers

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

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

from core.base import TRANSLATIONS
T = TRANSLATIONS("ui.dialogs.dialog_make_course_tables")

### +++++

from typing import Optional

from ui.ui_base import (
    ### QtWidgets:
    QWidget,
    ### QtGui:
    ### QtCore:
    Slot,
    ### other
    load_ui,
)
from core.list_activities import (
    read_from_db,
    make_teacher_table_pay,
    make_teacher_table_room,
    make_class_table_pdf,
    make_teacher_table_xlsx,
    make_class_table_xlsx,
    write_xlsx,
)

### -----


def exportTable(
    parent: Optional[QWidget] = None,
):

    ##### slots #####

    @Slot()
    def on_accepted():
        nonlocal result
        result = delta

#TODO
    @Slot()
    def on_pb_classes_clicked():
        """Export a pdf file with a table for each class detailing
        the lessons, etc.
        """
        pdfbytes = make_class_table_pdf(self.activities)
        filepath = SAVE_FILE("pdf-Datei (*.pdf)", T["class_lessons"])
        if filepath and os.path.isabs(filepath):
            if not filepath.endswith(".pdf"):
                filepath += ".pdf"
            with open(filepath, "wb") as fh:
                fh.write(pdfbytes)
            self.output(f"---> {filepath}")

#TODO
    @Slot()
    def on_pb_classes_xlsx_clicked(self):
        """Export an xlsx (Excel) file with a table for each class
        detailing the lessons, etc.
        The data is rather more "raw" than in the corresponding pdf file.
        """
        cdb = make_class_table_xlsx(self.activities)
        filepath = SAVE_FILE(
            "Excel-Datei (*.xlsx)", T["class_lessons"]
        )
        if filepath and os.path.isabs(filepath):
            if not filepath.endswith(".xlsx"):
                filepath += ".xlsx"
            write_xlsx(cdb, filepath)
                self.output(f"---> {filepath}")

    ##### functions #####

    def shrink():
        ui.resize(0, 0)

    def output(text):
        ui.output_box.appendPlainText(text)

    ##### dialog main ######

    # Don't pass a parent because that would add a child with each call of
    # the dialog.
    ui = load_ui("dialog_make_course_tables.ui", None, locals())

    # Data initialization: there is nothing to do.

    if parent:
        ui.move(parent.mapToGlobal(parent.pos()))
    # Activate the dialog
    ui.output_box.clear()
    ui.exec()




#old
class ExportTable:#(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        uic.loadUi(APPDATAPATH("ui/dialog_make_course_tables.ui"), self)

    def activate(self):
        """Open the dialog.
        """
        self.output_box.clear()
        self.activities = read_from_db()
        self.exec()

    def output(self, text):
        self.output_box.appendPlainText(text)

    @Slot()
    def on_pb_pay_clicked(self):
        """Export a pdf file with a table for each teacher detailing
        the workload and giving some pay-related information.
        """
        pdfbytes = make_teacher_table_pay(self.activities)
        filepath = SAVE_FILE("pdf-Datei (*.pdf)", T["teacher_workload_pay"])
        if filepath and os.path.isabs(filepath):
            if not filepath.endswith(".pdf"):
                filepath += ".pdf"
            with open(filepath, "wb") as fh:
                fh.write(pdfbytes)
            self.output(f"---> {filepath}")

    @Slot()
    def on_pb_teachers_clicked(self):
        """Export a pdf file with a table for each teacher detailing
        the lessons, etc.
        """
        pdfbytes = make_teacher_table_room(self.activities)
        filepath = SAVE_FILE("pdf-Datei (*.pdf)", T["teacher_activities"])
        if filepath and os.path.isabs(filepath):
            if not filepath.endswith(".pdf"):
                filepath += ".pdf"
            with open(filepath, "wb") as fh:
                fh.write(pdfbytes)
            self.output(f"---> {filepath}")


    @Slot()
    def on_pb_teachers_xlsx_clicked(self):
        """Export an xlsx (Excel) file with a table for each teacher
        detailing the workload and giving some pay-related information.
        The data is rather more "raw" than in the corresponding pdf files.
        """
        tdb = make_teacher_table_xlsx(self.activities)
        filepath = SAVE_FILE(
            "Excel-Datei (*.xlsx)", T["teacher_workload_pay"]
        )
        if filepath and os.path.isabs(filepath):
            if not filepath.endswith(".xlsx"):
                filepath += ".xlsx"
            write_xlsx(tdb, filepath)
            self.output(f"---> {filepath}")

