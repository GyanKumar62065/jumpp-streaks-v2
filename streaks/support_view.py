"""The support console: a user list and a per-user page. Renders engine output; no rules here.

The memorable element is the day strip: one tile per day, coloured by what happened.
"""

from html import escape
from urllib.parse import quote

from streaks.models import DayCode, StreakResult, User
from streaks.report import ListFilter, SupportRow, UserAction, UserListing

# What each day code looks like on the strip, and the plain-words label agents read.
_TONE_BY_CODE: dict[DayCode, str] = {
    DayCode.LEARNED: "flame",
    DayCode.LEARNED_LATE_SYNC: "flame",
    DayCode.PROTECTED_OUTAGE: "ice",
    DayCode.PROTECTED_FREEZE: "ice",
    DayCode.SKIPPED_TRAVEL: "ice",
    DayCode.PENDING: "pending",
    DayCode.TODAY_OPEN: "pending",
    DayCode.BELOW_THRESHOLD: "low",
    DayCode.REJECTED_TAMPER: "break",
    DayCode.REJECTED_TOO_LATE: "break",
    DayCode.NO_ACTIVITY: "break",
}
_LEGEND = (
    ("flame", "Counted"),
    ("flame late", "Counted, synced late"),
    ("ice", "Protected, streak kept"),
    ("pending", "Still open"),
    ("low", "Watched too little"),
    ("break", "Missed or rejected"),
)
_FILTER_LABELS = (
    (ListFilter.ALL, "Everyone"),
    (ListFilter.ACTION, "Needs action"),
    (ListFilter.BROKEN, "Broken streaks"),
    (ListFilter.PENDING, "Pending days"),
)
_STATUS_LABELS = {"ACTIVE": "Learned today", "AT_RISK": "Not yet today", "PENDING": "Waiting on a day", "BROKEN": "Streak broken"}

_CSS = """
:root{--paper:#F5F7FA;--ink:#1D2633;--muted:#5D6876;--line:#DCE1E8;--flame:#F76707;--ice:#4A8FE7;
--break:#C92A2A;--amber:#E0A800;--low:#AEB6C1;--card:#FFFFFF}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 "Avenir Next","Segoe UI",system-ui,sans-serif;
font-variant-numeric:tabular-nums}
a{color:inherit}
a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid var(--ice);outline-offset:2px}
.wrap{max-width:1040px;margin:0 auto;padding:28px 24px 64px}
.brand{display:flex;align-items:baseline;gap:12px;margin-bottom:24px}
.brand b{font-size:20px;letter-spacing:-.01em}
.brand span{color:var(--muted)}
h1{font-size:30px;line-height:1.15;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--muted);margin:0 0 20px}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:18px}
.toolbar input[type=search]{flex:1 1 220px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;font:inherit;background:var(--card)}
.chip{padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:var(--card);text-decoration:none;font-size:15px}
.chip[aria-current=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:middle}
th{font-size:14px;color:var(--muted);font-weight:600}
tr:last-child td{border-bottom:0}
tbody tr:hover{background:#F0F3F7}
.who a{font-weight:600;text-decoration:none;white-space:nowrap}
.who small{display:block;color:var(--muted)}
.num{font-weight:700;font-size:20px}
.status{font-size:14px;color:var(--muted)}
.todo{font-size:14px}
.todo.REFUND{color:var(--break);font-weight:600}.todo.TAMPER{color:var(--break)}
.strip{display:flex;gap:3px}
.tile{width:12px;height:22px;border-radius:3px;background:var(--low)}
.strip.big{gap:6px;flex-wrap:wrap}
.strip.big .tile{width:52px;height:64px;border-radius:8px;display:flex;flex-direction:column;justify-content:flex-end;
padding:6px;color:#fff;font-size:13px;font-weight:600;text-decoration:none}
.tile.flame{background:var(--flame)}.tile.ice{background:var(--ice)}.tile.break{background:var(--break)}
.tile.low{background:var(--low)}.tile.late{box-shadow:inset 0 0 0 3px var(--ink)}.tile.pending{background:transparent;border:2px dashed var(--amber)}
.strip.big .tile.pending{color:var(--ink)}
.nav{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;font-size:15px}
.nav .step{display:flex;gap:16px}
.hero{display:flex;flex-wrap:wrap;align-items:flex-end;gap:28px;margin-bottom:18px}
.count{font-size:96px;line-height:.9;font-weight:800;letter-spacing:-.04em}
.count small{display:block;font-size:16px;font-weight:500;letter-spacing:0;color:var(--muted);margin-top:8px}
.facts{color:var(--muted);margin:0;padding:0;list-style:none}
.facts li{margin:2px 0}
.banner{border-left:6px solid var(--ink);background:var(--card);padding:14px 18px;border-radius:6px;margin:0 0 26px;font-size:17px}
.banner.REFUND,.banner.TAMPER{border-color:var(--break)}.banner.PENDING{border-color:var(--amber)}
.banner.none{border-color:var(--flame);color:var(--muted)}
h2{font-size:19px;margin:30px 0 12px}
.matters{list-style:none;padding:0;margin:0}
.matters li{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:8px}
.matters b{display:inline-block;min-width:74px}
.code{font-size:13px;color:var(--muted)}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:14px;color:var(--muted);margin-top:12px}
.legend span{display:flex;align-items:center;gap:6px}
details summary{cursor:pointer;font-weight:600;margin:30px 0 12px}
.asof{display:flex;gap:8px;align-items:center;font-size:14px;color:var(--muted)}
.asof input{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;width:250px}
.asof button{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--ink);background:var(--ink);color:#fff;cursor:pointer}
.empty{background:var(--card);border:1px dashed var(--line);padding:24px;border-radius:10px;color:var(--muted)}
@media (max-width:640px){.count{font-size:72px}.hide-sm{display:none}.strip.big .tile{width:40px;height:52px}}
"""


def _as_of_suffix(raw_as_of: str | None, joiner: str = "?") -> str:
    return f"{joiner}as_of={quote(raw_as_of, safe='')}" if raw_as_of else ""


def compose_user_link(user_id: str, raw_as_of: str | None) -> str:
    return f"/support/{quote(user_id)}{_as_of_suffix(raw_as_of)}"


def _render_layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{_CSS}</style></head>
<body><main class="wrap">
<div class="brand"><b>🔥 Jumpp support</b><span>Streaks, day by day</span></div>
{body}
</main></body></html>"""


def _render_strip(result: StreakResult, *, is_big: bool) -> str:
    tiles = []
    for day in result.days:
        tone = _TONE_BY_CODE[day.code] + (" late" if day.code is DayCode.LEARNED_LATE_SYNC else "")
        tip = escape(f"{day.date:%d %b}: {day.code.value}. {day.detail}")
        label = f"<span>{day.date:%d}</span>" if is_big else ""
        tiles.append(f'<span class="tile {tone}" title="{tip}" role="img" aria-label="{tip}">{label}</span>')
    return f'<div class="strip{" big" if is_big else ""}">{"".join(tiles)}</div>'


def _render_legend() -> str:
    items = "".join(f'<span><i class="tile {tone}" aria-hidden="true"></i>{label}</span>' for tone, label in _LEGEND)
    return f'<div class="legend">{items}</div>'


def _render_as_of_form(action: str, raw_as_of: str | None, effective_as_of: str) -> str:
    value = escape(raw_as_of or effective_as_of)
    return f"""<form class="asof" method="get" action="{escape(action)}">
<label for="as_of">Showing what we knew at</label>
<input id="as_of" name="as_of" value="{value}">
<button type="submit">Update</button>
</form>"""


def _render_listing_row(listing: UserListing, raw_as_of: str | None) -> str:
    user, result, action = listing.user, listing.result, listing.action
    todo = (f'<span class="todo {action.kind.value}">{escape(action.text)}</span>' if action
            else '<span class="todo">Nothing to do</span>')
    return f"""<tr>
<td class="who"><a href="{compose_user_link(user.user_id, raw_as_of)}">{escape(user.name)}</a>
<small>{escape(user.user_id)}, {escape(user.plan)}</small></td>
<td class="num">{result.current_streak}</td>
<td class="status hide-sm">{escape(_STATUS_LABELS[result.status.value])}</td>
<td class="hide-sm">{_render_strip(result, is_big=False)}</td>
<td>{todo}</td>
</tr>"""


def render_support_index(
    listings: list[UserListing], active_filter: ListFilter, query: str, raw_as_of: str | None, effective_as_of: str
) -> str:
    chips = "".join(
        f'<a class="chip" href="/support?filter={value.value}{_as_of_suffix(raw_as_of, "&")}"'
        f' aria-current="{"true" if value is active_filter else "false"}">{label}</a>'
        for value, label in _FILTER_LABELS
    )
    rows = "\n".join(_render_listing_row(listing, raw_as_of) for listing in listings)
    table = (
        f"""<table><thead><tr><th scope="col">User</th><th scope="col">Streak</th><th scope="col" class="hide-sm">Today</th>
<th scope="col" class="hide-sm">Last days</th><th scope="col">What to do</th></tr></thead><tbody>{rows}</tbody></table>"""
        if listings else '<p class="empty">No users match. Clear the search or pick "Everyone".</p>'
    )
    hidden_as_of = f'<input type="hidden" name="as_of" value="{escape(raw_as_of)}">' if raw_as_of else ""
    body = f"""<h1>Who needs help</h1>
<p class="sub">{len(listings)} user{"" if len(listings) == 1 else "s"} shown. Open one to see each day and what to do.</p>
<form class="toolbar" method="get" action="/support" role="search">
<input type="search" name="q" value="{escape(query)}" placeholder="Search by name or user id" aria-label="Search users">
<input type="hidden" name="filter" value="{active_filter.value}">{hidden_as_of}
{chips}
</form>
{table}
{_render_legend()}
<p class="sub" style="margin-top:18px">{_render_as_of_form("/support", raw_as_of, effective_as_of)}</p>"""
    return _render_layout("Jumpp support: users", body)


def _render_banner(action: UserAction | None) -> str:
    if action is None:
        return '<p class="banner none">Nothing to do. The streak is correct as shown.</p>'
    return f'<p class="banner {action.kind.value}"><b>Do this:</b> {escape(action.text)}</p>'


def _render_days_that_matter(rows: list[SupportRow]) -> str:
    notable = [row for row in rows if row.code not in (DayCode.LEARNED, DayCode.TODAY_OPEN)]
    if not notable:
        return '<p class="sub">Every day counted normally.</p>'
    items = "".join(
        f'<li><b>{row.date:%d %b}</b> {escape(row.what_happened)}<br>'
        f'<span class="code">{row.code.value}. {escape(row.what_to_do)}</span></li>'
        for row in notable
    )
    return f'<ul class="matters">{items}</ul>'


def _render_day_table(rows: list[SupportRow]) -> str:
    body = "".join(
        f"<tr><td>{row.date:%a %d %b}</td><td>{row.code.value}</td><td>{escape(row.what_happened)}</td>"
        f"<td>{escape(row.what_to_do)}</td></tr>"
        for row in rows
    )
    return f"""<details><summary>Every day, newest first ({len(rows)})</summary>
<table><thead><tr><th scope="col">Date</th><th scope="col">Code</th><th scope="col">What happened</th>
<th scope="col">What to do</th></tr></thead><tbody>{body}</tbody></table></details>"""


def render_support_page(
    user: User,
    result: StreakResult,
    rows: list[SupportRow],
    action: UserAction | None,
    neighbours: tuple[str | None, str | None],
    raw_as_of: str | None,
) -> str:
    previous_id, next_id = neighbours
    steps = "".join(
        f'<a href="{compose_user_link(user_id, raw_as_of)}">{label} {escape(user_id)}</a>'
        for user_id, label in ((previous_id, "Previous:"), (next_id, "Next:")) if user_id
    )
    body = f"""<nav class="nav" aria-label="Users"><a href="/support{_as_of_suffix(raw_as_of)}">All users</a>
<span class="step">{steps}</span></nav>
<h1>{escape(user.name)}</h1>
<p class="sub">{escape(user.user_id)}, {escape(user.plan)} plan, home timezone {escape(user.home_tz)}</p>
<div class="hero">
<div class="count">{result.current_streak}<small>day streak</small></div>
<ul class="facts"><li>{escape(_STATUS_LABELS[result.status.value])}</li>
<li>Freezes left: {result.freezes_unused}</li><li>{escape(result.reason)}</li></ul>
</div>
{_render_banner(action)}
{_render_strip(result, is_big=True)}
{_render_legend()}
<h2>Days that matter</h2>
{_render_days_that_matter(rows)}
{_render_day_table(rows)}
<p class="sub" style="margin-top:24px">{_render_as_of_form(f"/support/{user.user_id}", raw_as_of, result.as_of.isoformat())}</p>"""
    return _render_layout(f"Jumpp support: {user.name}", body)
