"""
check_translations.py - last updated 2024-02-10

Update the translations file by parsing all source files, copying
information from the old translations file.


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

from configparser import ConfigParser
from string import Formatter
import os, sys
import ast

if __name__ == "__main__":
    this = sys.path[0]
    basedir = os.path.dirname(this)
    TRANSLATIONS_FILE = os.path.join(
        basedir, "program-data", "Translations.ini"
    )

### -----


def get_old_translations(filepath):
    trmap = {}
    cp = ConfigParser(
        interpolation = None,
        delimiters = ('=',),
        comment_prefixes = (';',)
    )
    cp.optionxform = str    # to stop case conversion for options
    cp.read(filepath, encoding = "utf-8")
    fmt = Formatter()
    for sec in sorted(cp.sections()):
        #print(sec)
        omap = {}
        trmap[sec] = omap
        for o in cp.options(sec):
            trtext = cp[sec][o]
            keys = {fname for _, fname, _, _ in fmt.parse(trtext) if fname}
            #print(f'  - {o}: {keys}')
            omap[o] = (keys, trtext)
    # The comments are filtered out
    return trmap


def get_tr_keys(root0, old_tr):
    errors = []
    new_tr = {}
    for (root, dirs, files) in os.walk(root0):
        dx = [d for d in dirs if d[0] in ('.', '_')]
        for d in dx:
            dirs.remove(d)
        fstrip = len(root0)
        for f in files:
            if f[0] != '.' and f.endswith(".py"):
                filepath = os.path.join(root, f)
                with open(filepath, "r") as source:
                    tree = ast.parse(source.read())
                v = Visitor(filepath[fstrip:], old_tr, new_tr)
                v.generic_visit(tree)
                errors += v._error_list
    return new_tr, errors


class Visitor(ast.NodeVisitor):
    def __init__(self, filepath: str, old_tr: dict, new_tr: dict):
        #print("§§§", filepath)
        self._file = filepath
        self._tr0 = old_tr
        self._tr = new_tr
        super().__init__()
        self.section = None
        self.section0 = None
        self._error_list = []

    def visit_Call(self, node):#func, args, keywords)
        if isinstance(node.func, ast.Name):
            #print(" " * self._indent, "§Nm", node.func.id)
            n = node.func.id
            l = node.lineno
            if n == "T":
                if len(node.args) != 1:
                    self._error("'T' needs 1 argument", line = l)
                    return
                _val = node.args[0]
                if (
                    not isinstance(_val, ast.Constant)
                    or not isinstance(_val.value, str)
                ):
                    self._error(
                        "'T' needs one literal string argument", line = l
                    )
                    return
                val = _val.value
                if self.section is None:
                    self._error(
                        f"'T' called ({val}) with no 'Tr' set", line = l
                    )
                    return
                # Check keys against old translation or previous use
                keys = {x.arg for x in node.keywords}
                try:
                    # Seek in old translations
                    keys0, tr0 = self.section0[val]
                except KeyError:
                    try:
                        # Seek in new translations
                        keys0, tr0, f0, l0 = self.section[val]
                    except KeyError:
                        self.section[val] = (keys, "", self._file, l)
                    else:
                        if keys != keys0:
                            self._error(
                                f"Message '{val}' used in {f0}, line {l0}"
                                " with different keys",
                                line = l
                            )
                else:
                    if keys == keys0:
                        if val not in self.section:
                            self.section[val] = (keys, tr0, self._file, l)
                    else:
                        self._error(
                            f"Message '{val}' has keys which differ from"
                            " those in the old translation",
                            line = l
                        )
            elif n == "Tr":
                if self.section is not None:
                    self._error("Repeated 'Tr' call", line = l)
                    return
                args = [x.value for x in node.args]
                if len(args) != 1:
                    self._error("'Tr' needs 1 argument", line = l)
                    return
                val = args[0]
                # See if another file has used this section
                try:
                    self.section = self._tr[val]
                except KeyError:
                    self.section = {}
                    self._tr[val] = self.section
                try:
                    self.section0 = self._tr0[val]
                except KeyError:
                    self.section0 = {}
        self.generic_visit(node)

    def _error(self, message, line):
        self._error_list.append(
            f"*** ERROR in {self._file}:\n  line {line}: {message}"
        )

def write_translation(filepath, trmap):
    cp = ConfigParser(
        interpolation = None,
        delimiters = ('=',),
        comment_prefixes = (';',)
    )
    cp.optionxform = str    # to stop case conversion for options
    for sec in sorted(trmap):
        cp[sec] = {}
        omap = ntran[sec]
        for k in sorted(omap):
            keys, tr, f, l = omap[k]
            if not tr:
                tr = "TODO " + " ".join(f'{{{x}}}' for x in keys)
            cp[sec][k] = tr
    with open(filepath, "w", encoding = "utf-8") as fh:
        cp.write(fh)


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#


if __name__ == "__main__":
    ifile = TRANSLATIONS_FILE
    print(f"\n  ***** Old Translations ({ifile}) *****")
    trmap = get_old_translations(ifile)
    for s in sorted(trmap):
        print("\n§:", s)
        omap = trmap[s]
        for o in sorted(omap):
            print(f'  - {o}: {omap[o]}')

    print("\n ===================================================")
    print("\n  ***** New Translations ****")
    ntran, elist = get_tr_keys(this, trmap)
    for sec in sorted(ntran):
        omap = ntran[sec]
        print(f"\n[{sec}]")
        for k in sorted(omap):
            print(f"   -- {k}:", omap[k])
            keys, tr, f, l = omap[k]

    ofile = os.path.join(os.path.dirname(ifile), "New_Translations.ini")
    write_translation(ofile, ntran)

    print("\n ***************************************************")
    for e in elist:
        print(e)
