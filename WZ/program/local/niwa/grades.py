"""
local/niwa/grades.py

Last updated:  2024-01-20

Regional support for grade handling:
    Waldorfschule in Niedersachsen


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

if __name__ == "__main__":
    import sys, os

    this = sys.path[0]
    appdir = os.path.dirname(os.path.dirname(this))
    sys.path[0] = appdir
    basedir = os.path.dirname(appdir)
    from core.base import setup
    setup(os.path.join(basedir, 'TESTDATA'))

#from core.base import Tr
#T = Tr("local.grades")

### +++++

from core.basic_data import print_fix

### -----


def int_ave(nlist: list[int]):
    """Calculated the rounded average of a list of integers.
    """
    d = len(nlist)
    return (sum(nlist) + d//2) // d


def grade_tables(grade_map: dict[str, tuple[str, int]]):
    """Build conversion tables for grades on the given scale to/from
    integer values starting at 0 (lowest grade).
    This assumes that such a conversion is meaningful in the context of
    the intended usage (in particular for the calculation of averages)!
    Return two items:
        - grade -> integer vaue mapping (value -1 => skip in calculations),
        - list of "normal" grades in ascending order (used to convert
          value to grade).
    """
    grade_list = []
    grade_val = {}
    for g, data in grade_map.items():
        v = data[1]
        if v >= 0:
            grade_list.append((v, g))
            grade_val[g] = v
        elif v == -1:
            grade_val[g] = v    # skipped in calculations
        # Others are not valid in calculations
    return grade_val, [g for _, g in sorted(grade_list)]


class GradeArithmetic:
    def __init__(self, scale: str):
        self.grade_val, self.grade_list = grade_tables(scale)
        print("\n§grade_val:", self.grade_val)
        print("\n§grade_list:", self.grade_list)

#TODO: I might need more information about the columns?

    def function(self, data: dict, col_values: list[str]):
        f = getattr(self, data["__f__"])
        return f(data, col_values)

    def COMPOSITE(self, data: dict, col_values: list[str]) -> str:
        """Calculate the average of the given grades.
        Return the result as a grade.
        If any "illegal" grades are passed, the result will be
        parenthesized. Non-numerical grades which are not "illegal"
        will be skipped.
        """
        grades = [col_values[c] for c in data["__COLUMNS__"]]
        igrades = []
        incomplete = False
        for g in grades:
            try:
                gi = self.grade_val[g]
                if gi >= 0:
                    igrades.append(gi)
            except KeyError:
                incomplete = True
        if igrades:
            gs = self.grade_list[int_ave(igrades)]
            return f"({gs})" if incomplete else gs
        return ""

    def AVERAGE(self, data: dict, col_values: list[str]) -> str:
        """Calculate the average of the given grades.
        Return the result as a fixed-point number with the given number
        of decimal places. If the number of decimal places is negative,
        the result will be truncated rather than rounded. In that case,
        the number of decimal places is <-1 - decimal_places> (this is
        to allow 0 decimal places although -0 is not distinguishable from 0).
        If any "illegal" grades are passed, the result will be
        parenthesized. Non-numerical grades which are not "illegal"
        will be skipped.
        """
        grades = [col_values[c] for c in data["__COLUMNS__"]]
        decimal_places = data.get("decimal_places") or -2
        if decimal_places >= 0:
            truncate = False
        else:
            decimal_places = -1 - decimal_places
            truncate = True
        igrades = []
        incomplete = False
        for g in grades:
            if g.startswith("("):
                # "Incomplete" composites are parenthesized.
                g = g.strip("()")
                incomplete = True
            try:
                # Use <self.grade_val[g]> to determine whether the grade
                # is necessary for the calculation of a complete average,
                # but get the value from the original grade.
                gi = self.grade_val[g]
                if gi >= 0:
                    igrades.append(int(g.rstrip("+-")))
            except KeyError:
                incomplete = True
        if igrades:
            ave = sum(igrades) / len(igrades)
        else:
            return ""
        if truncate:
            # Round to string with extra decimal places to avoid
            # unlikely (but maybe possible?) errors arising from
            # the floating point storage.
            aves = print_fix(
                ave,
                decimal_places + 2,
                strip_trailing_zeros = False
            )
            if decimal_places == 0:
                decimal_places += 1     # to eliminate the decimal separator
            aves = aves[:-decimal_places]
        return f"({aves})" if incomplete else aves


# --#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#--#

if __name__ == "__main__":
    from core.basic_data import get_database
    get_database()  # ensure CONFIG is initialized
    from grades.grade_tables import valid_grade_map

    for nl in [
        (3, 7, 9, 5, 0, 2, 13),
        (8, 9, 12, 15, 14, 7, 15, 3, 11),
        (5, 3, 4, 7, 8, 2, 9, 6),
    ]:
        print(f"%int_ave({nl}) =", int_ave(nl), f"({sum(nl) / len(nl)})")

    for sc in "SEK_I", "SEK_II":
        print(f"\n{sc}:")
        gmap = valid_grade_map(sc)
        grade_val, val_grade = grade_tables(gmap)
        print("  %grade_val:", grade_val)
        print("  %grade_list:", val_grade)
