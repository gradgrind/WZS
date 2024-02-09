from configparser import ConfigParser
from string import Formatter
import os

cp = ConfigParser(
    interpolation = None,
    delimiters = ('=',),
    comment_prefixes = (';',)
)
cp.optionxform = str    # to stop case conversion for options
cp.read('../../program-data/Translations.ini', encoding = "utf-8")
fmt = Formatter()
for sec in sorted(cp.sections()):
    print(sec)
    for o in cp.options(sec):
        keys = [fname for _, fname, _, _ in fmt.parse(cp[sec][o]) if fname]
        print(f'  - {o}: {keys}')

# The comments are filtered out
with open("Translations2.ini", "w", encoding = "utf-8") as fh:
    cp.write(fh)

print("\n  ***** .py files ****")
for (root,dirs,files) in os.walk('..'):
    print(root)
    dx = [d for d in dirs if d[0] in ('.', '_')]
    for d in dx:
        dirs.remove(d)
    for f in files:
        if f[0] != '.' and f.endswith(".py"):
            print("   -", f)


quit(100)

import ast
import pprint

f = "../grades/odt_grade_reports.py"
f = "../core/basic_data.py"
with open(f, "r") as source:
    tree = ast.parse(source.read())

#print(ast.dump(tree, indent=2))
#quit(1)

class Visitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self._indent = 0
        self.collected = []

    def _visit(self, node):
        print(" " * self._indent, node)
        self._indent += 2
        self.generic_visit(node)
        self._indent -= 2

    def visit_Call(self, node):#func, args, keywords)
        if isinstance(node.func, ast.Name):
            print(" " * self._indent, "§Nm", node.func.id)
            if node.func.id in ("T", "Tr"):
                self.collected.append(node)
        elif isinstance(node.func, ast.Attribute):
            print(" " * self._indent, "§Att", node.func.value)
        else:
            print(" " * self._indent, node)
        self._indent += 2
        self.generic_visit(node)
        self._indent -= 2


v = Visitor()
v.generic_visit(tree)

print("\n ===============================================\n")
for c in v.collected:
    print([x.value for x in c.args], [x.arg for x in c.keywords])
