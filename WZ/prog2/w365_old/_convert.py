import xmltodict
import json
import os
from itertools import product

AG_SEP = "."

infile = "Waldorf_365_Demo2.xml"
'''
with open("test00.xml", "r", encoding = "utf-8") as fh:
    xmlin = fh.read()
jsonin = xmltodict.parse(xmlin)
print(jsonin)

print("\n -------------------------")
import xml.parsers.expat

# 3 handler functions
def start_element(name, attrs):
    print('Start element:', name, attrs)
def end_element(name):
    print('End element:', name)
def char_data(data):
    print('Character data:', repr(data))

p = xml.parsers.expat.ParserCreate()

p.StartElementHandler = start_element
p.EndElementHandler = end_element
p.CharacterDataHandler = char_data

p.Parse(xmlin)


quit(1)
'''

'''
import uuid

for i in range(10):
    print(uuid.uuid4())
'''

def xml2json(filepath):
    b, s = os.path.basename(filepath).split(".")
    outpath = os.path.join(os.path.dirname(filepath), b + ".json")
    with open(filepath, "r", encoding = "utf-8") as fh:
        xmlin = fh.read()
    jsonout = json.dumps(xmltodict.parse(xmlin), indent = 2)
    with open(outpath, "w", encoding = "utf-8") as fh:
        fh.write(jsonout)
    return True

'''
xml2json("test01.fet")
'''
xml2json(infile)
#'''

with open(infile, "r", encoding = "utf-8") as fh:
    xmlin = fh.read()
jsonin = xmltodict.parse(xmlin)

scenario = jsonin["File"]["Scenario"]

fetout = {}
idmap = {}

def abs_cat(x):
    a = x["@Absences"]
    absences = {}
    if a:
        alist = [id2absence[id] for id in a.split(",")]
        alist.sort()
        for day, hour in alist:
            try:
                absences[day].append(hour)
            except KeyError:
                absences[day] = [hour]
        print("Absences:", absences)
    c = x["@Categories"]
    catlist = []
    if c:
        for id in c.split(","):
            catlist.append(id2category[id])
        print("Categories:", catlist)
    return absences, catlist


class AG(frozenset):
    def __repr__(self):
        return f"{{*{', '.join(sorted(self))}*}}"

    def __str__(self):
        return AG_SEP.join(sorted(self))


def make_class_groups(classtag, divs):
    if not divs:
        return {
            "Name": classtag,
            "Number_of_Students": "0",
            #"Comments": "",
            # The information regarding categories, divisions of each category,
            # and separator is only used in the divide year automatically by
            # categories dialog in fet.
            "Number_of_Categories": "0",
            "Separator": AG_SEP,
        }
    cgmap = {
        "Name": classtag,
        "Number_of_Students": "0",
        #"Comments": "",
        # The information regarding categories, divisions of each category,
        # and separator is only used in the divide year automatically by
        # categories dialog in fet.
        "Number_of_Categories": "1",
        "Separator": AG_SEP,
    }
    # Check the input
    gset = set()
    divs1 = []
    divs1x = []
    for d in divs:
        gs = set()
        xg = {}
        divs1.append(gs)
        divs1x.append(xg)
        for g in d:
            assert g not in gset
            gset.add(g)
            try:
                g, subs = g.split("=", 1)
            except ValueError:
                gs.add(g)   # A "normal" group
            else:
                # A "compound" group
                xl = []
                xg[g] = xl
                for s in subs.split("+"):
                    assert s not in xl
                    xl.append(s)
        for g, sl in xg.items():
            assert len(sl) > 1
            for s in sl:
                assert s in gs
        assert len(gs) > 1
    # Generate "atomic" groups
    g2ag = {}
    aglist = []
    for p in product(*divs1):
        ag = AG(p)
        aglist.append(ag)
        #print(ag)
        for g in p:
            try:
                g2ag[g].add(ag)
            except KeyError:
                g2ag[g] = {ag}
    for xg in divs1x:
        for g, gl in xg.items():
            ags = set()
            for gg in gl:
                ags.update(g2ag[gg])
            g2ag[g] = ags
    # Add "categories" (atomic groups)
    cgmap["Category"] = {
        "Number_of_Divisions": f"{len(aglist)}",
        "Division": [str(ag) for ag in aglist],
    }
    # Add groups and subgroups
    groups = []
    cgmap["Group"] = groups
    # If there is only one division, the fet-groups can be the same as
    # fet-subgroups. If there are "compound" groups, these will contain
    # "normal" groups, which then do not need additional fet-group
    # entries.
    if len(divs1) == 1:
        pending = []
        done = set()
        for g in sorted(g2ag):
            agl = g2ag[g]
            if len(agl) == 1:
                pending.append(g)
            else:
                subgroups = [
                    {
                        "Name": f"{classtag}{AG_SEP}{str(ag)}",
                        "Number_of_Students": "0",
                        #"Comments": "",
                    }
                    for ag in agl
                ]
                groups.append({
                    "Name": f"{classtag}{AG_SEP}{g}",
                    "Number_of_Students": "0",
                    #"Comments": "",
                    "Subgroup": subgroups,
                })
                #print(f">>> {g} -> {agl}")
                done.update(list(ag)[0] for ag in agl)
        for g in pending:
            if g not in done:
                groups.append({
                    "Name": f"{classtag}{AG_SEP}{g}",
                    "Number_of_Students": "0",
                    #"Comments": "",
                })
                #print(f">>> {g}")
    else:
        for g in sorted(g2ag):
            agl = g2ag[g]
            subgroups = [
                {
                    "Name": f"{classtag}{AG_SEP}{str(ag)}",
                    "Number_of_Students": "0",
                    #"Comments": "",
                }
                for ag in agl
            ]
            groups.append({
                "Name": f"{classtag}{AG_SEP}{g}",
                "Number_of_Students": "0",
                #"Comments": "",
                "Subgroup": subgroups,
            })
            #print(f">>> {g} -> {agl}")
    #print("$g2ag:", g2ag)
    return cgmap

'''
print("\n%%", make_class_groups("10K", ()))
print("\n%%", make_class_groups("12G", (("A", "B"), ("G", "R"))))
print("\n%%", make_class_groups("08", (("A", "B"),)))
print("\n%%", make_class_groups("11", [["A","BG","R","G=A+BG","B=BG+R"]]))
print("\n%%", make_class_groups(
    "13", [["k","m","s","K=m+s","M=k+s","S=k+m"],["MaE","MaG"]]
))
quit(1)
'''

#==========================================================

X = "Day"
print(f"\n*** {X} ***")
xlist = []
for d in scenario[X]:
    print(" --", d)
#    idmap[d["@Id"]] = (X, d)
    xlist.append({"Name": d["@Shortcut"]})
fetout["Days_List"] = {
    "Number_of_Days":   f"{len(xlist)}",
    "Day": xlist,
}

X = "TimedObject"
print(f"\n*** {X} ***")
xlist = []
lunchbreak = []
for p in scenario[X]:
    print(" --", p)
#    idmap[p["@Id"]] = (X, p)
    # It seems to be acceptable to have no @Shortcut.
    # In that case, use @ListPosition?
    sc = p["@Shortcut"] or p["@ListPosition"]
    xlist.append({"Name": sc})
    if p["@MiddayBreak"] == "true":
        lunchbreak.append(sc)
print("\n§Lunchbreak:", lunchbreak)
fetout["Hours_List"] = {
    "Number_of_Hours":   f"{len(xlist)}",
    "Hour": xlist,
}

X = "Category"
print(f"\n*** {X} ***")
id2category = {}
for x in scenario[X]:
#    idmap[x["@Id"]] = (X, p)
    id2category[x["@Id"]] = {
        k: x[k]
        for k in (
            "@Name", "@Shortcut", "@Colliding", "@NoReport", "@Role",
            "@ScheduleFactor", "@WorkloadFactor"
        )
    }
    print(" --", id2category[x["@Id"]])

X = "Absence"
print(f"\n*** {X} ***")
id2absence = {}
for d in scenario[X]:
    #print(" --", d)
#    idmap[d["@Id"]] = (X, d)
    mode =  d["@mode"]
    id2absence[d["@Id"]] = (d["@day"], d["@hour"])

X = "Room"
print(f"\n*** {X} ***")
id2room = {}
xlist = []
for d in scenario[X]:
    print(" --", d)
    assert not d["@RoomGroup"]
#    idmap[d["@Id"]] = (X, d)
    amap, clist = abs_cat(d)
    id2room[d["@Id"]] = (d["@Shortcut"], d["@Name"])
    xlist.append({
        "Name": d["@Shortcut"],
        #"Building": "",
        "Capacity": d["@capacity"] or "30000",
        "Virtual": "false",
        "Comments": d["@Name"],
    })
fetout["Rooms_List"] = {
    "Room": xlist,
}

X = "Subject"
print(f"\n*** {X} ***")
xlist = []
id2subject = {}
for d in scenario[X]:
    #print(" --", d)
#    idmap[d["@Id"]] = (X, d)
    amap, clist = abs_cat(d)
    id2subject[d["@Id"]] = (d["@Shortcut"], d["@Name"])
    xlist.append({"Name": d["@Shortcut"], "Comments": d["@Name"]})
fetout["Subjects_List"] = {
    "Subject": xlist,
}

X = "Teacher"
print(f"\n*** {X} ***")
xlist = []
tconstraints = {}
id2teacher = {}
for d in scenario[X]:
    print(" --", d)
#    idmap[d["@Id"]] = (X, d)
    amap, clist = abs_cat(d)
    tid = d["@Shortcut"]
    id2teacher[d["@Id"]] = (tid, d["@Name"])
    xlist.append({
        "Name": tid,
        "Target_Number_of_Hours": "0",
        "Qualified_Subjects": None,
        "Comments": f'{d["@Firstname"]} {d["@Name"]}'
    })
    tconstraints[tid] = {
        f: d[f]
        for f in (
            "@MaxDays",
            "@MaxLessonsPerDay",
            "@MaxWindowsPerDay",    # gaps
            "@MinLessonsPerDay",
            "@NumberOfAfterNoonDays",
        )
    }
fetout["Teachers_List"] = {
    "Teacher": xlist,
}
print("\n§tconstraints:", tconstraints)

X = "Group"
print(f"\n*** {X} ***")
id2gtag = {}
for d in scenario[X]:
    #print(" --", d)
#    idmap[d["@Id"]] = (X, d)
    amap, clist = abs_cat(d)
    id2gtag[d["@Id"]] = d["@Shortcut"]

#print("\n&&&", list(scenario))

X = "GradePartiton"
print(f"\n*** {X} ***")
id2div = {}
#divid2gidlist = {}
for d in scenario[X]:
    #print(" --", d)
#    idmap[d["@Id"]] = (X, d)
    pos = d["@ListPosition"]    # "0.0", "1.0", ...
    name = d["@Name"]
    gidlist = d["@Groups"].split(",")
#    glist = [id2gtag[g] for g in gidlist]
    iglist = []
    id2div[d["@Id"]] = iglist
#    divid2gidlist[d["@Id"]] = gidlist
    for gid in gidlist:
        iglist.append((gid, id2gtag[gid]))
    print(f" -- {pos}: {name} = {iglist}")

ylist = []  # Collect class data for fet
fetout["Students_List"] = {
    "Year": ylist,
}
X = "Grade" # classes
print(f"\n*** {X} ***")
id2grade = {}
id2group = {}
for d in scenario[X]:
    #print(" --", d)
#    idmap[d["@Id"]] = (X, d)
    amap, clist = abs_cat(d)
# @ClassTeacher
    for f in (
        #"Level", "Letter", "Groups",
        "ForceFirstHour", "NumberOfAfterNoonDays",
        "MaxLessonsPerDay", "MinLessonsPerDay",
        "Name", "Shortcut",
        #"Students",
        #"SubjectMappings"
    ):
        print(f"  @{f}:", repr(d[f"@{f}"]))

    cltag = f'{d["@Level"]}{d["@Letter"]}'
    id2grade[d["@Id"]] = cltag
    id2group[d["@Id"]] = cltag
    dlist = []
    divs = d["@GradePartitions"]
    if divs:
        for div in divs.split(","):
            glist = []
            for gid, g in id2div[div]:
                glist.append(g)
                id2group[gid] = f"{cltag}{AG_SEP}{g}"
            dlist.append(glist)
    print(f'+++ {cltag}: {dlist}')
    ylist.append(make_class_groups(cltag, dlist))
    print("  -----------------------------------------")

#fetout["Activities_List"] = {"Activity": self.activities},
fetout["Buildings_List"] = None,
#fetout["Rooms_List"] = {"Room": fet_rooms},

X = "Course"
print(f"\n*** {X} ***")
id2course = {}
for d in scenario[X]:
#    show = d["@Absences"] or d["@Categories"]
    slist = d["@Subjects"].split(",")
    tlist = d["@Teachers"].split(",")
#    if len(tlist) > 1:
    if True:
#    if show:
#    if d["@HoursPerWeek"] == "0.0":
        print("\n ------")
        vmap = {}
        id2course[d["@Id"]] = vmap
        for k, v in d.items():
            if k == "@Categories" and v:
                v = id2category[v]
            elif k == "@Groups" and v:
                gidlist = v.split(",")
                v = ", ".join(id2group[gid] for gid in gidlist)
            elif k == "@Subjects" and v:
                v = ", ".join(str(id2subject[s]) for s in slist)
            elif k == "@Teachers" and v:
                v = ", ".join(str(id2teacher[t]) for t in tlist)
            elif k == "@PreferredRooms" and v:
                rlist = v.split(",")
                v = ", ".join(str(id2room[r]) for r in rlist)
            print(f"  {k}:", str(v)[:60])
            vmap[k] = v
#    idmap[d["@Id"]] = (X, d)

quit(1)

X = "Lesson"
print(f"\n*** {X} *** ???")
lesson_map = {}
#nmap = {}
n = 0
for d in scenario[X]:
    lesson_map[d["@Id"]] = d
    continue

    day = d["@Day"]
    hour = d["@Hour"]
    if day == "2" and hour == "0":
        n += 1
        #print("\n ------", d)
    #if d["@Fixed"] == "true":
    #if d["@Course"] == "":
    if (d['@EpochPlan'] == '271baf6f-151b-4354-b50c-add01622cb10'
        and d['@EpochPlanGrade'] == '22216d17-04a4-488e-a585-ecb69021e20f'
    ):
        print("\n ------", d)

print("\n$$$", n)
#    if int(day) > 4:
#        if hour != "0":
#            print("\n ------", d)   ... none!
#    try:
#        nmap[day] += 1
#    except KeyError:
#        nmap[day] = 1

'''
if int(day) <= 4:       # TODO: number of days???
    hour = d["@Hour"]
    cid = d["@Course"]
    if cid:
        print("  --", day, hour, id2course.get(cid) or cid)
    else:
        print("  ++", d)
        # Look at @EpochPlan and @EpochPlanGrade
'''

#    if d["@EpochPlan"]:
#        print("  ++", d)

#print("\n§§§'Day' frequencies:", nmap)

X = "EpochPlan"
epochs = {}
#course_map = {}
print(f"\n*** {X} *** ???")
for d in scenario[X]:
    outlines = []
    epochs[d["@Id"]] = d["@Name"]
#    outlines.append(f'### {d["@Name"]}\n')
    for l in d["@Lessons"].split(","):
        ln = lesson_map.pop(l)
        outlines.append(f"   -- {ln}")
        c = ln["@Course"]
#        try:
#            course_map[c] += 1
#        except KeyError:
#            course_map[c] = 1
        outlines.append(f"   >> {id2course[c]}\n")

    with open(f'xxout_{d["@Name"]}', "w", encoding = "utf-8") as fh:
        fh.write("\n".join(outlines))


#with open("xxout1a", "w", encoding = "utf-8") as fh:
#    fh.write(
#        "\n".join(f"   --{n}: {id2course[c]}"
#        for c, n in course_map.items())
#    )

#outlines.append("\n=================================================\n")
# From the following data it is possible to extract the classes and
# lessons (times – are they always fixed? ... perhaps assume not?) for
# each of the "Epochenplans".
outlines = []
elns = {}
lnids = []
for lnid, ln in lesson_map.items():
    epid = ln["@EpochPlan"]
    if epid:
        try:
            elns[epochs[epid]].append(ln)
        except KeyError:
            elns[epochs[epid]] = [ln]
        lnids.append(lnid)
for ep, lnlist in elns.items():
    outlines.append(f"\n ### {ep}")
    for ln in lnlist:
        outlines.append(f"  ++ {ln}")
for lnid in lnids:
    del lesson_map[lnid]

with open("xxout", "w", encoding = "utf-8") as fh:
    fh.write("\n".join(outlines))

# the remaining lessons
#course_set = {ln["@Course"] for ln in lesson_map.values()}
#with open("xxout2a", "w", encoding = "utf-8") as fh:
#    fh.write("\n".join(f"   -- {id2course[c]}" for c in course_set))

#with open("xxout2", "w", encoding = "utf-8") as fh:
#    fh.write("\n".join(f"   -- {ln}" for ln in lesson_map.values()))


quit(0)

fetout["@version"] = "6.18.0"
fetbase = {"fet": fetout}
print("\n  ==>")
print(xmltodict.unparse(fetbase, pretty=True, indent="  "))
