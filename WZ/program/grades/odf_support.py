"""
grades/odf_support.py - last updated 2024-01-23

Support functions for working with odf-documents (LibreOffice).


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

import os

if __name__ == "__main__":
    import sys

    this = sys.path[0]
    appdir = os.path.dirname(this)
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

#from core.base import Tr
#T = Tr("grades.odf_support")

### +++++

import platform, subprocess     #, tempfile

from core.base import REPORT_OUT, REPORT_ERROR
from core.basic_data import CONFIG

### -----

#TODO
### Messages
_COMMANDNOTPOSSIBLE = "Befehl '{cmd}' konnte nicht ausgeführt werden"
#_NOPDF              = "Keine PDF-Datei wurde erstellt"

#----------------------------------------------------------------------#


def run_extern(command, *args, cwd = None, xpath = None, feedback = None):
    """Run an external program.
    Pass the command and the arguments as individual strings.
    The command must be either a full path or a command known in the
    run-time environment (PATH).
    Named parameters can be used to set:
     - cwd: working directory. If provided, change to this for the
       operation.
     - xpath: an additional PATH component (prefixed to PATH).
     - feedback: If provided, it should be a function. It will be called
         with each line of output as this becomes available.
    Return a tuple: (return-code, message).
    return-code: 0 -> ok, 1 -> fail, -1 -> command not available.
    If return-code >= 0, return the output as the message.
    If return-code = -1, return a message reporting the command.
    """
    # Note that using the <timeout> parameter will probably not work,
    # at least not as one might expect it to.
    params = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'universal_newlines':True
    }
    my_env = os.environ.copy()
    if platform.system() == 'Windows':
        # Suppress the console
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        params['startupinfo'] = startupinfo
    if xpath:
        # Extend the PATH for the process
        my_env['PATH'] = xpath + os.pathsep + my_env['PATH']
        params['env'] = my_env
    if cwd:
        # Switch working directory for the process
        params['cwd'] = cwd

    cmd = [command] + list(args)
    try:
        if feedback:
            out = []
            with subprocess.Popen(cmd, bufsize=1, **params) as cp:
                for line in cp.stdout:
                    l = line.rstrip()
                    out.append(l)
                    feedback(l)
            msg = '\n'.join(out)

        else:
            cp = subprocess.run(cmd, **params)
            msg = cp.stdout

        return (0 if cp.returncode == 0 else 1, msg)

    except FileNotFoundError:
        return (-1, _COMMANDNOTPOSSIBLE.format(cmd=repr(cmd)))

#TODO?
#def spawn_extern(*args):
#    subprocess.Popen(args, stdin = subprocess.DEVNULL,
#            stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)


#TODO: switch from pikepdf to pypdf
def merge_pdf(ifile_list: list[str], pad2sided: int=0) -> bytes:
    """Join the pdf-files in the input list <ifile_list> to produce a
    single pdf-file. The output is returned as a <bytes> object.
    The parameter <pad2sided> allows blank pages to be added
    when input files have an odd number of pages – to ensure that
    double-sided printing works properly. It can take the value 0 (no
    padding), 1 (padding if odd number of pages, but more than 1 page)
    or 2 (padding if odd number of pages).
    """
    pdf = Pdf.new()
    for ifile in ifile_list:
        src = Pdf.open(ifile)
        pdf.pages.extend(src.pages)
        if pad2sided and (len(src.pages) & 1):
            if pad2sided != 1 or len(src.pages) > 1:
                page = Page(src.pages[0])
                w = page.trimbox[2]
                h = page.trimbox[3]
                pdf.add_blank_page(page_size=(w, h))
    bstream = BytesIO()
    pdf.save(bstream)
    return bstream.getvalue()


def libre_office(odf_list, pdf_dir, show_output=False):
    """Convert a list of odf-files to pdf-files.
    The input files are provided as a list of absolute paths,
    <pdf_dir> is the absolute path to the output folder.
    If <show_output> is true, LibreOffice output will be displayed.
    """
    # Use LibreOffice to convert the odt-files to pdf-files.
    # If using the appimage, the paths MUST be absolute, so I use absolute
    # paths "on principle".
    # I don't know whether the program blocks until the conversion is complete
    # (some versions don't), so it might be good to check that all the
    # expected files have been generated (with a timeout in case something
    # goes wrong?).
    # The old problem that libreoffice wouldn't work headless if another
    # instance (e.g. desktop) was running seems to be no longer the case,
    # at least on linux.
    def extern_out(line):
        if show_output:
            REPORT_OUT(line)

    try:
        lo = CONFIG.LIBREOFFICE
    except KeyError:
#TODO
        REPORT_ERROR(
            "No LIBREOFFICE configuration (execution command) in CONFIG"
        )
        return
    rc, msg = run_extern(
        lo,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        pdf_dir,
        *odf_list,
        feedback=extern_out
    )


