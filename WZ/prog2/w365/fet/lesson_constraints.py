"""
w365/fet/lesson_constraints.py - last updated 2024-03-24

Set fixed lesson times.
Handle prevention of multiple lessons in one subject on any day.


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


#TODO: Constraint generation, tidying


from w365.wz_w365.class_groups import AG_SEP


class SubjectGroupActivities:
    def __init__(self, atomic_groups):
        self.atomic_groups = atomic_groups
        self.sid_g_aids = {}

    def add_activities(self,
        sid: str,
        groups: list[str],
        activity_ids: list[str]
    ) -> None:
        """Add groups/activities to the collection for the given subject.
        """
        for g in groups:
            for ag in self.atomic_groups[g]:
                sid_g = (sid, ag)
                try:
                    self.sid_g_aids[sid_g].update(activity_ids)
                except KeyError:
                    self.sid_g_aids[sid_g] = set(activity_ids)


def lesson_constraints(db, fetout, daylist, periodlist):
    """Add constraints to specify activity times.
    Add constraints to ensure that multiple lessons in any subject
    are not placed on the same day.
    """
    #print("\n§LESSONS:")
    fixed_activities = {}
    fet_fixed = []
    constraint_list = fetout["Time_Constraints_List"]
    constraint_list["ConstraintActivityPreferredStartingTime"] = fet_fixed
    for node in db.tables["LESSONS"]:
        assert node["FIXED"] == "true"
        #print("  --", node)
        course_key = node["_Course"]
        course = db.key2node[course_key]
        activities = course["$ACTIVITIES"]
        #print("    ++", activities)

        nodelen = node["LENGTH"]
        for a in activities:
            aid = a["Id"]
            if aid in fixed_activities:
                continue
            if a["Duration"] == nodelen:
                fixed_activities[aid] = node
                fet_fixed.append({
                    "Weight_Percentage": "100",
                    "Activity_Id": aid,
                    "Preferred_Day": daylist[int(node["DAY"])],
                    "Preferred_Hour": periodlist[int(node["PERIOD"])],
                    "Permanently_Locked": "true",
                    "Active": "true",
                    "Comments": None,
                })
                break
        else:
            assert False, "No suitable activity found"
#TODO: Is <fixed_activities> what I need, and should it be save (to
# <db> structure?)
    #print("\nfixed_activities:")
    #for aid, node in fixed_activities.items():
    #    print("\n  ***", aid)
    #    print(node)

    print("\n§subject_activities:")
    print(db.subject_activities.sid_g_aids)

# db.subject_activities.sid_g_aids.values() produces sets which
# probably include duplicates. Convert these to frozensets and add them
# to the initial collection

#TODO: rather make a dict with length as key? (see below)
    activity_groups = {
        frozenset(ags)
        for ags in db.subject_activities.sid_g_aids.values()
        if len(ags) > 1
    }
    print("\n  ==>>", activity_groups)

#TODO--
    return

# Need to associate the lessons with the corresponding activities

# I need to map a class_group to its atoms (including class prefix):
# db.full_atomic_groups
# Then for every subject and atomic group I should have a list/set of
# activities. These need to be constrained.

#???
    # Order according to set length
    kag2aids: dict[str, list[str]]
    aids: set[str]
    aidset_map: dict[int, set[frozenset[str]]] = {}



    for sid, aid_group in db.subject_activities.items():
        for aids in kag2aids.values():
            n = len(aids)
            if n > 1:   # skip sets with only one element
                aids_fs = frozenset(aids)
                try:
                    aidset_map[n].add(aids_fs)
                except KeyError:
                    aidset_map[n] = {aids_fs}
    ### Eliminate subsets
    lengths = sorted(aidset_map, reverse = True)
    newsets = aidset_map[lengths[0]]  # the largest sets
    for l in lengths[1:]:
        xsets = set()
        for aidset in aidset_map[l]:
            for s in newsets:
                if aidset < s:
                    break
            else:
                xsets.add(aidset)
        newsets.update(xsets)
    ### Sort the sets, build the constraint
    aids_list = sorted([sorted(s) for s in newsets])
    for aids in aids_list:
        for a in aids:
#TODO: This may not be optimal. Fixed lessons could rather be handled by
# blocking their days for the others. This would leave fewer to be
# mutually exclusive, if < 2 no further constraint would then be needed.
            # If all are locked, no constraint is at all.
            if a not in starttimes:
                constraints.append(
                    {
                        "Weight_Percentage": "100",
                        "Consecutive_If_Same_Day": "true",
                        "Number_of_Activities": str(len(aids)),
                        "Activity_Id": aids,
                        "MinDays": "1",
                        "Active": "true",
                        "Comments": None,
                    }
                )
                break
