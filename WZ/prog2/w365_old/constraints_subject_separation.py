

#TODO: Handle prevention of multiple lessons in one subject on any day.


from fet_support import AG_SEP


class SubjectGroupActivities:
    def __init__(self, class_group_atoms: dict[str, dict]):
        self.class_group_atoms = class_group_atoms
        self.subject_activities = {}

    def subject_group_activity(self,
        sid: str,
        groups: list[str],
        activity_ids: list[str]
    ) -> None:
        """Add groups/activities to the collection for the given subject.
        """
        try:
            kag2aids = self.subject_activities[sid]
        except KeyError:
            kag2aids = {}
            self.subject_activities[sid] = kag2aids
        for group in groups:
            # Associate the activity ids with the atomic groups
            try:
                klass, g = group.split(AG_SEP, 1)
            except ValueError:
                klass = group
                g = ""
            agset = self.class_group_atoms[klass][g]
            if agset:
                for ag in agset:
                    kag = f"{klass}{AG_SEP}{ag}"
                    try:
                        kag2aids[kag].update(activity_ids)
                    except KeyError:
                        kag2aids[kag] = set(activity_ids)
            else:
                try:
                    kag2aids[group].update(activity_ids)
                except KeyError:
                    kag2aids[group] = set(activity_ids)


    def constraint_day_separation(self,
        starttimes: dict[str, dict],
        constraints: list[dict]
    ):
        """Add constraints to ensure that multiple lessons in any subject
        are not placed on the same day.
        """
        # Order according to set length
        kag2aids: dict[str, list[str]]
        aids: set[str]
        aidset_map: dict[int, set[frozenset[str]]] = {}
        for sid, kag2aids in self.subject_activities.items():
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
