"""SVG card renderer for the profile README (layout and palette from the Figma design)."""
import textwrap
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

BG, CARD, CARD2, CHIP = "#0f131d", "#171b26", "#0a0e18", "#262a35"
CYAN, GREEN, PURPLE, RED = "#4cd7f6", "#4edea3", "#b395ff", "#ffb4ab"
TEXT, BODY, MUTED = "#dfe2f1", "#bcc9cd", "#869397"
MONO = "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',monospace"
SANS = "'Space Grotesk','Segoe UI',Helvetica,Arial,sans-serif"
W = 830
CW = 7.0  # mono char width at 11px


def t(x, y, s, size=11, fill=BODY, font=MONO, weight=400, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(str(s))}</text>')


def rect(x, y, w, h, fill, r=4, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w:.1f}" height="{h}" rx="{r}" fill="{fill}" {extra}/>'


def wrap(x, y, s, width_chars, size=13, fill=BODY, lh=20, font=SANS):
    out, cy = [], y
    for line in textwrap.wrap(s, width_chars):
        out.append(t(x, cy, line, size, fill, font))
        cy += lh
    return "".join(out), cy


def chips(x, y, items, max_w, fill=CHIP, color=BODY, size=11):
    out, cx, cy = [], x, y
    for it in items:
        w = len(it) * CW + 16
        if cx + w > x + max_w:
            cx, cy = x, cy + 28
        out.append(rect(cx, cy, w, 22, fill, 3) + t(cx + 8, cy + 15, it, size, color))
        cx += w + 6
    return "".join(out), cy + 22


def header(y, label, right):
    return (t(0, y, label.upper(), 11, CYAN, extra='letter-spacing="0.55"')
            + f'<rect x="{len(label)*7.4+8:.0f}" y="{y-4}" width="48" height="1" fill="{CYAN}" opacity="0.4"/>'
            + t(W, y, right, 11, MUTED, anchor="end"))


def svg(h, body, pad=0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="#2a3566"/><stop offset="0.55" stop-color="#171d36"/>'
            f'<stop offset="1" stop-color="{BG}"/></linearGradient>'
            f'<radialGradient id="glow"><stop offset="0" stop-color="{CYAN}" stop-opacity="0.18"/>'
            f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect width="{W}" height="{h}" fill="{BG}"/>{body}</svg>')


def hero(handle, name, role, school, tagline, location, status):
    b = rect(0, 0, W, 300, "url(#g)", 14)
    b += '<circle cx="700" cy="40" r="170" fill="url(#glow)"/>'
    b += rect(24, 96, W - 48, 180, "#171b26", 10, 'opacity="0.92"')
    sw = len(status) * CW + 34
    b += rect(48, 120, sw, 20, "#1f3a36", 10) + f'<circle cx="62" cy="130" r="4" fill="{GREEN}"/>'
    b += t(74, 134, status, 11, GREEN)
    b += rect(48 + sw + 8, 120, len(handle) * CW + 12, 20, CHIP, 3) + t(48 + sw + 14, 134, handle, 11, MUTED)
    b += t(48, 188, name, 40, TEXT, SANS, 700, extra='letter-spacing="-1"')
    b += (f'<text x="48" y="220" font-family="{SANS}" font-size="17" fill="{BODY}">{escape(role)}  ·  '
          f'<tspan fill="{TEXT}" font-weight="600">{escape(school)}</tspan></text>')
    b += rect(48, 238, len(tagline) * CW + 40, 24, "#1c1f2a", 5) + t(60, 254, f'"{tagline}"', 11, CYAN)
    b += t(48 + len(tagline) * CW + 52, 254, "|   " + location, 11, BODY)
    return svg(300, b)


def focus(updated_label, intern, aegis):
    b = header(14, "// 01: Core trajectory", updated_label)
    cw1, cw2, y0 = 470, 340, 30

    def card(x, w, d, accent):
        s = rect(x, y0, w, 356, CARD, 8)
        s += rect(x + 24, y0 + 22, len(d["badge"]) * CW + 10, 18, accent, 2, 'fill-opacity="0.13"') + t(x + 29, y0 + 35, d["badge"], 11, accent)
        s += t(x + w - 24, y0 + 35, d["meta"], 11, MUTED, anchor="end")
        s += (f'<text x="{x+24}" y="{y0+74}" font-family="{SANS}" font-size="22" font-weight="700" fill="{TEXT}" xml:space="preserve">'
              f'{escape(d["title"])}<tspan fill="{accent}">{escape(d.get("title2",""))}</tspan></text>')
        body, cy = wrap(x + 24, y0 + 102, d["desc"], int((w - 48) / 6.6), 13, BODY, 20)
        s += body
        cy += 8
        for i, (k, v, c) in enumerate(d["metrics"]):
            if d["style"] == "grid":
                mw = (w - 48 - 16) / 3
                mx = x + 24 + i * (mw + 8)
                s += rect(mx, cy, mw, 66, CARD2, 4) + t(mx + 8, cy + 18, k, 10, MUTED)
                s += t(mx + 8, cy + 42, v, 20, c, SANS, 700) + t(mx + 8, cy + 58, d["sub"][i], 10, BODY)
            else:
                s += rect(x + 24, cy + i * 34, w - 48, 28, CARD2, 3) + t(x + 34, cy + i * 34 + 18, k, 11, BODY)
                s += t(x + w - 34, cy + i * 34 + 18, v, 11, c, weight=500, anchor="end")
        c2, _ = chips(x + 24, y0 + 296, d["chips"], w - 48)
        return s + c2
    b += card(0, cw1, intern, CYAN) + card(cw1 + 16, cw2 + 4, aegis, GREEN)
    return svg(y0 + 366, b)


def heatmap_card(x, w, h, all_days, commits, streak_cur, streak_long):
    day = {d: c for d, c in all_days}
    end = datetime.utcnow().date()
    start = end - timedelta(days=52 * 7 + end.weekday() + 1)
    s = rect(x, 0, w, h, CARD, 8) + t(x + 24, 34, "Commit Velocity (last 52 weeks)", 12, TEXT, weight=500)
    badge = f"{commits:,} Commits"
    s += rect(x + w - 24 - len(badge) * CW - 16, 20, len(badge) * CW + 16, 20, CHIP, 2) + t(x + w - 32, 34, badge, 11, CYAN, anchor="end", weight=500)
    s += rect(x + 24, 54, w - 48, 98, CARD2, 4)
    vals = sorted(c for c in day.values() if c)
    q = [vals[int(len(vals) * p)] if vals else 1 for p in (0.25, 0.5, 0.75)]
    cols = ["#1c1f2a", "#12414d", "#1b7f94", "#32b3cf", CYAN]
    d, col, last_m = start, 0, None
    while d <= end:
        wd = (d.weekday() + 1) % 7  # Sunday first
        if wd == 0 and d != start:
            col += 1
        c = day.get(d.isoformat(), 0)
        lvl = 0 if c == 0 else 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4
        cx = x + 34 + col * ((w - 78) / 52.5)
        if cx < x + w - 44:
            s += f'<rect x="{cx:.1f}" y="{62 + wd*12}" width="11" height="9" rx="2" fill="{cols[lvl]}"/>'
            if d.month != last_m and wd == 0 and col > 1:
                s += t(cx, 150, d.strftime("%b"), 9, MUTED)
                last_m = d.month
        d += timedelta(days=1)
    for i, (k, v) in enumerate([("Current streak", f"{streak_cur} days"), ("Longest streak", f"{streak_long} days")]):
        bw = (w - 48 - 8) / 2
        bx = x + 24 + i * (bw + 8)
        s += rect(bx, 162, bw, h - 176, CARD2, 4) + t(bx + bw / 2, 180, k, 10, MUTED, anchor="middle")
        s += t(bx + bw / 2, 200, v, 16, TEXT, SANS, 700, "middle")
    return s


def langs_card(x, w, h, langs):
    pal = [CYAN, GREEN, PURPLE, "#353944", RED, MUTED]
    s = rect(x, 0, w, h, CARD, 8) + t(x + 24, 34, "Codebase Share", 12, TEXT, weight=500)
    s += t(x + w - 24, 34, "by repo size", 11, MUTED, anchor="end")
    s += rect(x + 24, 50, w - 48, 12, CARD2, 6)
    cx = x + 24
    for i, (n, p) in enumerate(langs):
        sw = (w - 48) * p / 100
        s += f'<rect x="{cx:.1f}" y="50" width="{max(sw,1):.1f}" height="12" fill="{pal[i % 6]}"/>'
        cx += sw
    for i, (n, p) in enumerate(langs):
        y = 90 + i * 24
        s += f'<circle cx="{x+28}" cy="{y-4}" r="4" fill="{pal[i % 6]}"/>' + t(x + 40, y, n, 11, TEXT) + t(x + w - 24, y, f"{p}%", 11, BODY, weight=500, anchor="end")
    return s


def leetcode_card(x, w, h, lc, rating, top_pct):
    total, e, m, hd = lc
    s = rect(x, 0, w, h, CARD, 8) + t(x + 24, 34, "Algorithmic Proficiency", 12, TEXT, weight=500)
    s += rect(x + w - 24 - 84, 20, 84, 20, "#1f3a36", 2) + t(x + w - 32, 34, f"{total}+ Solved", 11, GREEN, anchor="end", weight=500)
    s += t(x + 24, 84, str(rating), 36, TEXT, SANS, 700) + t(x + 24 + len(str(rating)) * 22 + 10, 84, "Max Contest Rating", 11, MUTED)
    tot = max(e + m + hd, 1)
    for i, (n, v, c) in enumerate([] if e + m + hd == 0 else [("Easy", e, CYAN), ("Medium", m, GREEN), ("Hard", hd, PURPLE)]):
        y = 112 + i * 30
        s += t(x + 24, y, n, 11, BODY) + t(x + w - 24, y, f"{v}", 11, c, weight=500, anchor="end")
        s += rect(x + 24, y + 6, w - 48, 6, CARD2, 3) + rect(x + 24, y + 6, max((w - 48) * v / tot, 2), 6, c, 3)
    if top_pct:
        s += rect(x + 24, h - 34, w - 48, 22, CARD2, 2) + t(x + 32, h - 19, "Global Ranking Percentile", 11, MUTED)
        s += t(x + w - 32, h - 19, f"Top {top_pct}% Worldwide", 11, GREEN, anchor="end", weight=500)
    return s


def telemetry(all_days, commits, cur, longest, langs, lc, rating, top_pct, live_label):
    b = header(14, "// 02: Telemetry & velocity", live_label)
    inner = f'<g transform="translate(0,30)">{heatmap_card(0, W, 230, all_days, commits, cur, longest)}</g>'
    inner += f'<g transform="translate(0,276)">{langs_card(0, 405, 250, langs)}{leetcode_card(425, 405, 250, lc, rating, top_pct)}</g>'
    return svg(30 + 276 + 250 + 4, b + inner)


def arch(cards):
    b = header(14, "// 03: Architecture blueprints", "Production grade implementations")
    cw = (W - 24) / 2
    for i, d in enumerate(cards):
        x = i * (cw + 24)
        s = rect(x, 30, cw, 520, CARD, 8)
        s += t(x + 24, 62, d["sys"], 11, d["accent"], weight=500) + rect(x + 24 + len(d["sys"]) * CW + 8, 49, len(d["tag"]) * CW + 10, 18, CHIP, 2) + t(x + 24 + len(d["sys"]) * CW + 13, 62, d["tag"], 11, BODY)
        ty = 92
        for ln in d["title"]:
            s += t(x + 24, 30 + ty, ln, 20, TEXT, SANS, 700)
            ty += 26
        body, cy = wrap(x + 24, 30 + ty + 8, d["desc"], int((cw - 48) / 6.6), 13, BODY, 20)
        s += body
        fy = cy + 8
        s += rect(x + 24, fy, cw - 48, 96, CARD2, 4) + t(x + 40, fy + 22, d["flow_label"], 10, MUTED, extra='letter-spacing="0.55"')
        bw = (cw - 48 - 32 - 16) / 3
        for j, (a, bb, c) in enumerate(d["flow"]):
            bx = x + 40 + j * (bw + 8)
            s += rect(bx, fy + 36, bw, 46, CHIP, 2) + t(bx + bw / 2, fy + 54, a, 11, c, anchor="middle", weight=500) + t(bx + bw / 2, fy + 70, bb, 10, MUTED, anchor="middle")
        by = fy + 96 + 22
        for ln in d["bullets"]:
            lines = textwrap.wrap(ln, int((cw - 70) / 6.3))
            s += t(x + 24, by, "›", 13, d["accent"], SANS, 700)
            for k, l in enumerate(lines):
                s += t(x + 40, by + k * 18, l, 12, BODY, SANS)
            by += 18 * len(lines) + 8
        c2, _ = chips(x + 24, 30 + 520 - 40, d["chips"], cw - 48, "#1c1f2a", d["accent"])
        b += s + c2
    return svg(30 + 520 + 4, b)


def skills(cats):
    b = header(14, "// 04: Technical stack matrix", "Kernel & stack runtime")
    b += rect(0, 30, W, 190, CARD, 8)
    cw = (W - 48 - 4 * 16) / 5
    for i, (name, color, items) in enumerate(cats):
        x = 24 + i * (cw + 16)
        b += t(x, 62, name.upper(), 11, color, weight=500, extra='letter-spacing="0.55"')
        c, _ = chips(x, 76, items, cw, CHIP, TEXT, 10)
        b += c
    return svg(228, b)


def achievements(items):
    b = header(14, "// 05: Honors & verified milestones", "Deterministic records")
    cw = (W - 3 * 12) / 4
    for i, (sub, big, desc, c) in enumerate(items):
        x = i * (cw + 12)
        b += rect(x, 30, cw, 176, CARD, 8) + rect(x + 16, 46, 28, 28, c, 4, 'fill-opacity="0.13"')
        b += t(x + 16, 96, sub, 10, MUTED)
        b += t(x + 16, 120, big, 18, TEXT, SANS, 700)
        body, _ = wrap(x + 16, 142, desc, int((cw - 32) / 6.2), 11.5, BODY, 16)
        b += body
    return svg(214, b)
