"""
w365/fet/lesson_constraints.py - last updated 2024-05-15

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


from w365.class_groups import AG_SEP


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
        Use "atomic" groups rather than the normal "division" groups.
        """
        for g in groups:
            for ag in self.atomic_groups[g]:
                sid_g = (sid, ag)
                try:
                    self.sid_g_aids[sid_g].update(activity_ids)
                except KeyError:
                    self.sid_g_aids[sid_g] = set(activity_ids)

    def get_activity_groups(self):
        """<self.sid_g_aids.values()> probably contains many duplicate
        activity groups. Convert these groups to frozensets to filter
        out duplicates. Collect the resulting sets of frozensets
        according to number of entries (activity-ids).
        """
        activity_groups = {}
        for ags in self.sid_g_aids.values():
            ll = len(ags)
            if ll > 1:
                fs = frozenset(ags)
                try:
                    activity_groups[ll].add(fs)
                except KeyError:
                    activity_groups[ll] = {fs}
        return activity_groups


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
    for nid in db.node_tables["LESSONS"]:
        node = db.nodes[nid]
        assert node["FIXED"] == "true"
        #print("  --", node)
        course_key = node["_Course"]
        course = db.nodes[course_key]
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

    # Collect the activity-id sets according to their length
    activity_groups = db.extra["subject_activities"].get_activity_groups()
    #print("\n  ==>>", activity_groups)

    ### Eliminate subsets
    lengths = sorted(activity_groups, reverse = True)
    newsets = activity_groups[lengths[0]]  # the largest sets
    for l in lengths[1:]:
        xsets = set()
        for aidset in activity_groups[l]:
            for s in newsets:
                if aidset < s:
                    break
            else:
                xsets.add(aidset)
        newsets.update(xsets)
    ### Sort the sets, build the constraint
    fet_daybetween = constraint_list["ConstraintMinDaysBetweenActivities"]
    aids_list = sorted([sorted(s) for s in newsets])
    for aids in aids_list:
        for aid in aids:
#TODO: This may not be optimal. Fixed lessons could rather be handled by
# blocking their days for the others. This would leave fewer to be
# mutually exclusive, if < 2 no further constraint would then be needed.
            # If all are locked, no constraint is needed.
            if aid not in fixed_activities:
                fet_daybetween.append(
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
