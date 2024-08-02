#let PAGE_HEIGHT = 210mm
#let PAGE_WIDTH = 297mm
#let PAGE_BORDER = (top:15mm, bottom: 12mm, left: 15mm, right: 15mm)
#set page(height: PAGE_HEIGHT, width: PAGE_WIDTH,
//  numbering: "1",
  margin: PAGE_BORDER,
)
#let CELL_BORDER = 1pt
#let BIG_SIZE = 16pt
#let NORMAL_SIZE = 14pt
#let PLAIN_SIZE = 12pt
#let SMALL_SIZE = 10pt

#let TITLE_HEIGHT = 20mm
#let PLAN_AREA_HEIGHT = (PAGE_HEIGHT - PAGE_BORDER.top
    - PAGE_BORDER.bottom - TITLE_HEIGHT)
#let PLAN_AREA_WIDTH = (PAGE_WIDTH - PAGE_BORDER.left
    - PAGE_BORDER.right)

//#PLAN_AREA_WIDTH x #PLAN_AREA_HEIGHT

#let DAYS = ("Mo", "Di", "Mi", "Do", "Fr")
#let HOURS = ("HU 1", "HU 2",
    "FS 1", "FS 2", "FS 3", "FS 4", "FS 5", "FS 6", "FS 7")
#let TIMES = (
    ((8, 10), (9, 0)),
    ((9, 0), (9, 50)),
    ((10, 10), (10, 55)),
    ((11, 0), (11, 45)),
    ((12, 0), (12, 45)),
    ((12, 50), (13, 35)),
    ((13, 45), (14, 30)),
    ((14, 30), (15, 15)),
    ((15, 15), (16, 0)),
)


#let tend = TIMES.at(-1).at(1)
#let tstart = TIMES.at(0).at(0)
#let tdelta = (tend.at(0)*60 + tend.at(1)
    - tstart.at(0)*60 + tstart.at(1))
#let vfactor = PLAN_AREA_HEIGHT / tdelta
//#vfactor

#let period_time(t1, t2) = (
    datetime(hour: t1.at(0), minute: t1.at(1), second: 0
    ).display("[hour]:[minute]")
    + " – "
    + datetime(hour: t2.at(0), minute: t2.at(1), second: 0
    ).display("[hour]:[minute]")
)

#let H_HEADER_HEIGHT = 15mm
#let V_HEADER_WIDTH = 30mm

// Collect headers and start and end coordinates for the period rows.
#let hlines = ()
#let trows = (H_HEADER_HEIGHT,)
#let t0 = 0
#let tx = 0
#let ptime = ()
#let i = 0
#for (pt1, pt2) in TIMES {
    let t1 = (pt1.at(0)*60 + pt1.at(1)) * vfactor
    let t2 = (pt2.at(0)*60 + pt2.at(1)) * vfactor
    if t0 == 0 {
        t0 = t1
        tx = t2
    } else {
        trows.push(t1 - tx)
        tx = t2
        ptime.push("")
    }
    hlines.push((t1 - t0 + H_HEADER_HEIGHT, t2 - t0 + H_HEADER_HEIGHT))
    trows.push(t2 - t1)
    ptime.push(HOURS.at(i) + "|" + period_time(pt1, pt2))
    i += 1
}
//#trows
//#hlines
//#ptime

// Build the vertical lines

#let vlines = (V_HEADER_WIDTH,)
#let colwidth = (PLAN_AREA_WIDTH - V_HEADER_WIDTH) / DAYS.len()
#let d0 = V_HEADER_WIDTH
//COLWIDTH #colwidth
#for d in DAYS {
    d0 += colwidth
    vlines.push(d0)
}
#let tcolumns = (V_HEADER_WIDTH,) + (colwidth,)*DAYS.len()
//#tcolumns
//#vlines


#let ch = ([],) + DAYS
#for h in ptime {
    ch += (h,) + ([],) * DAYS.len()
}

#show table.cell: it => {
  if it.y == 0 {
    set text(size: BIG_SIZE, weight: "bold")
    align(center + horizon, it.body.at("text", default: ""))
  } else if it.x == 0 {
    //it.body.fields()
    let txt = it.body.at("text", default: "")
    let t1t2 = txt.split("|")
    let tt = text(size: NORMAL_SIZE, weight: "bold", t1t2.at(0))
    if t1t2.len() > 1 {
        tt += [\ ] + text(size: PLAIN_SIZE, t1t2.at(1))
    }
    align(center + horizon, tt)
  } else {
    it
  }
}

// On lines with two text items:
// If one is smaller than 25% of the space, leave this and shrink the
// other to 90% of the reamining space. Otherwise shrink both.
#let fit2inspace(width, text1, text2) = {
    let t1 = text(size: SMALL_SIZE, text1)
    let t2 = text(size: SMALL_SIZE, text2)
    let w4 = width / 4
    context {
        let s1 = measure(t1)
        let s2 = measure(t2)
        if (s1.width + s2.width) > width * 0.9 {
            if s1.width < w4 {
                // shrink only text2
                let w2 = width - s1.width
                let scl = (w2 * 0.9) / s2.width
                box(width: width, inset: 2pt,
                    t1
                    + h(1fr)
                    + text(size: scl * SMALL_SIZE, text2)
                )
            } else if s2.width < w4 {
                // shrink only text1
                let w2 = width - s2.width
                let scl = (w2 * 0.9) / s1.width
                box(width: width, inset: 2pt,
                    text(size: scl * SMALL_SIZE, text1)
                    + h(1fr)
                    + t2
                )
            } else {
                // shrink both
                let scl = (width * 0.9) / (s1.width + s2.width)
                box(width: width, inset: 2pt,
                    text(size: scl * SMALL_SIZE, text1)
                    + h(1fr)
                    + text(size: scl * SMALL_SIZE, text2)
                )
            }
        } else {
            box(width: width, inset: 2pt, t1 + h(1fr) + t2)
        }
    }
}

#let fitinspace(width, textc) = {
    let t = text(size: NORMAL_SIZE, weight: "bold", textc)
    context {
        let s = measure(t)
        if s.width > width * 0.9 {
            let scl = (width * 0.9 / s.width)
            let ts = text(size: scl * NORMAL_SIZE, weight: "bold", textc)
            box(width: width, h(1fr) + ts + h(1fr))
        } else {
            box(width: width, h(1fr) + t + h(1fr))
        }
    }
}

#let cell_inset = CELL_BORDER
#let cell_width = colwidth - cell_inset * 2

#let ttcell(
    day: 0,
    hour: 0,
    duration: 1,
    offset: 0,
    fraction: 1,
    total: 1,
    centre: "",
    tl: "",
    tr: "",
    bl: "",
    br: "",
) = {
    let (y0, y1) = hlines.at(hour)
    let x0 = vlines.at(day)
    if duration > 1 {
        y1 = hlines.at(hour + duration - 1).at(1)
    }
    let wfrac = cell_width * fraction / total
    let xshift = cell_width * offset / total
    // Shrink excessively large components.
    let b = box(
        fill: luma(100%),
        stroke: CELL_BORDER,
        inset: 0pt,
        height: y1 - y0 - CELL_BORDER*2,
        width: wfrac,
    )[
        #fit2inspace(wfrac, tl, tr)
        #v(1fr)
        #fitinspace(wfrac, centre)
        #v(1fr)
        #fit2inspace(wfrac, bl, br)
    ]
    place(top + left,
        dx: x0 + CELL_BORDER + xshift,
        dy: y0 + CELL_BORDER,
        b
    )
}

//#context here().position()
#let tbody = table(
    columns: tcolumns,
    rows: trows,
    gutter: 0pt,
    stroke: rgb("#ff7001"),
    inset: 0pt,
    fill: (_, y) =>
        if y != 0 and ptime.at(y - 1) == "" { luma(220) },
//  align: center + horizon,
    ..ch
)

#show heading: it => text(weight: "bold", size: BIG_SIZE,
    bottom-edge: "descender",
    pad(left: 5mm, it))

#let dict = (day: 2, hour: 5, centre: "Eu", tl: "ET", br: "eUS")

#let xdata = json(sys.inputs.ifile)

#let page = 0
#for (k, kdata) in xdata.Pages [
    #{
        if page != 0 {
            pagebreak()
        }
        page += 1
    }

    = #k

    #box([
        #tbody
        #for kd in kdata {
            ttcell(..kd)
        }
    ])
]
