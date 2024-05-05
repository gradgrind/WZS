"""
io_support/odf_pdf_merge.py - last updated 2024-05-05

Automate conversion of odf-documents (LibreOffice) to pdf and the
merging of pdf files.


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

#from core.wzbase import Tr
#T = Tr("io_support.odf_pdf_merge")

### +++++

import os, platform, subprocess

from pypdf import PdfWriter

from core.wzbase import SYSTEM, REPORT_OUT, REPORT_ERROR

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

def merge_pdf(infiles: list[str], outfile: str, pad2sided: int = 0):
    """Join the pdf-files in the input list <infiles> to produce a
    single pdf-file, <outfile>.
    The parameter <pad2sided> allows blank pages to be added
    when input files have an odd number of pages – to ensure that
    double-sided printing works properly. It can take the value 0 (no
    padding), 1 (padding if odd number of pages, but more than 1 page)
    or 2 (padding if odd number of pages).
    """
    merger = PdfWriter()
    pcount = 0
    for pdf in infiles:
        merger.append(pdf)
        _pcount = pcount
        pcount = len(merger.pages)
        n = pcount - _pcount
        if (n & 1) and (pad2sided > 1 or (pad2sided == 1 and n > 2)):
            merger.add_blank_page()
    merger.write(outfile)
    merger.close()


def libre_office(odf_list, pdf_dir, show_output = False):
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
    rc, msg = run_extern(
        SYSTEM["LIBREOFFICE"],
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        pdf_dir,
        *odf_list,
        feedback=extern_out
    )
