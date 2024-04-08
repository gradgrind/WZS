# Testing algorithms. Of course any really usable code would not be
# written in python, but this can perhaps serve as a rough template.


class Constraint:
    """Use this as the base class for all (hard?) constraints.
    It provides an interface for describing a conflict.
    """
#TODO: basically everything
    __slots__ = (
        "c_type",
        "c_description",
    )

#    def __init__(self):
#        pass

    def describe(self):
        return self.cc_text


# Maybe the subclasses should be in a different module?
# Note: must take duration into account

class ConstraintDayEnd(Constraint):
# Only relevant for duration > 1
    __slots__ = ()
    cc_text = "NO_SPACE_AT_END_OF_DAY"    # use T()


class ConstraintClassNotAvailable(Constraint):
    __slots__ = ("class_tag",)
    cc_text = "CLASS_NOT_AVAILABLE{c}"    # use T()

    def __init__(self, class_tag):
        self.class_tag = class_tag

    def describe(self):
        return self.cc_text.format(c = self.class_tag)


class ConstraintTeacherNotAvailable(Constraint):
    __slots__ = ("teacher_tag",)
    cc_text = "TEACHER_NOT_AVAILABLE{t}"    # use T()

    def __init__(self, teacher_tag):
        self.teacher_tag = teacher_tag

    def describe(self):
        return self.cc_text.format(t = self.teacher_tag)


class ConstraintFixedActivity(Constraint):
    __slots__ = ("activity_ref",)
    cc_text = "CONFLICTING_ACTIVITY{a}"    # use T()

    def __init__(self, activity):
#TODO: Use ref or index? If using index, how do I get at the activity
# itself?
        self.activity_ref = activity

    def describe(self):
        return self.cc_text.format(a = str(self.activity_ref))





class CoreConstraints:
    __slots__ = (
        "teacher_weeks",
        "class_weeks",
    )

    def __init__(self, teachers, classes):
        self.teacher_weeks = [0] * len(teachers)
        self.class_weeks = [0] * len(classes)

# Another structure might have advantages, but whether that would make
# much difference in the end? Keep it straightforward at first.

class Activity:
    __slots__ = (
        "core_constraints",
# Alternatively, core_constraints can be passed in to each method
# needing it ...
        "available_slots",
# An array containing 0 (?) in available slots, otherwise the reason
# for the blockage. HOW?!
# That can be an unavailable teacher, with tag, an unavailable class,
# with tag, one or more fixed activities, with reference, end-of-day for
# activities with length >1, possibly other constraints ...
# For a basic test, the value only needs to be non-0, but to give
# background information, it could perhaps be a list of constraint
# descriptors, or some such. This would suggest using a base class for
# all constraint-like things with at least the information required
# here. It would be helpful if this structure didn't lead to too much
# duplication.
    )

    def __init__(self, core_constraints):
        self.core_constraints = core_constraints

# Here it would be good to have


    def test_slot(self, slot: int) -> bool:
# Return list of clashing activities? That could make the operation
# quite a bit more expensive because if only a True/False result is
# expected, processing can be aborted as soon as a clash is found.
# Wait and see which form is actually needed!

# Do I need to check whether the length causes a "day overflow"?
# Having a static list/set of slots which are in principle acceptable
# for this activity, taking into account length and fixed allocations,
# non-availabilities, etc., could improve efficiency here.
        ll0 = self.duration
        constraints = self.core_constraints
        for t in self.teachers:
            slots = constraints.teacher_weeks[t]
            ll = ll0
            while True:
                if slots[slot]:     # the clashing activity
                    return False
                if ll == 1:
                    break
                slot += 1
                ll -= 1
# However, it might be neater to handle the multiple slots more or
# less separately, each as a whole in itself. The individual tests
# would then be more compact and clearer.

        for c, g in self.classes:
            # I assume multiple groups in a single class are lumped together

            if constraints.class_weeks[c][slot] & g:
                return False
# How do I get the activity here?
# Having an array for every atomic group could lead to quite costly
# allocations (an activity can cover many atomic groups). A class can
# have only a rather limited number of activities in a single slot, so
# it might be better to have a list of activities for each class. I
# would need to go through this list looking for conflicts.

# Because of the possibility of an activity clashing on several points,
# any collection of clashing activities would need to work like a set,
# to avoid duplication (though elimination of duplicates could happen
# at a less time-critical point, so a list might be acceptable). It is
# probably sensible to avoid maps if possible.


    def __str__(self):
        return "TODO: Activity"

