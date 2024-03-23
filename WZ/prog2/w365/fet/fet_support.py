# Support functions for fet

#AG_SEP = ":"    # Separator for "atomic" groups, etc.

SUBJECT_LUNCH_BREAK = ".lb"
SUBJECT_FREE_AFTERNOON = ".pm"


def next_activity_id(reset = False):
    global _activity_id
    if reset:
        _activity_id = 0
    else:
        _activity_id += 1
    return _activity_id


