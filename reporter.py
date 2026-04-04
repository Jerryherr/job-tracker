"""
Generate self-contained HTML reports — unified template for initial + weekly runs.
"""
import json, logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio
from jinja2 import Environment, BaseLoader
from config import JOB_CATEGORIES, VERTICAL_DOMAINS, COMPANIES, REPORTS_DIR

logger = logging.getLogger(__name__)

CAT_MAP = {c["key"]: c for c in JOB_CATEGORIES}
CAT_MAP["other"] = {"key": "other", "label": "Other", "color": "#9E9E9E"}

def _cat_label(key): return CAT_MAP.get(key, CAT_MAP["other"])["label"]
def _cat_color(key): return CAT_MAP.get(key, CAT_MAP["other"])["color"]
def _dom_label(key): return VERTICAL_DOMAINS.get(key, {}).get("label", key)
def _dom_color(key): return VERTICAL_DOMAINS.get(key, {}).get("color", "#9E9E9E")
def _company_label(key): return COMPANIES.get(key, {}).get("label", key)
def _company_color(key): return COMPANIES.get(key, {}).get("color", "#555")
def _fig_html(fig, first=False):
    return pio.to_html(fig, full_html=False, include_plotlyjs="cdn" if first else False, config={"responsive": True})
def _ts(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

# ── chart builders ─────────────────────────────────────────────────────────

def _chart_dept_breakdown(jobs, company_key, top_n=15):
    """Horizontal bar chart of native department/team counts for one company."""
    co_jobs = [j for j in jobs if j["company"] == company_key]
    dept_counts = Counter(j.get("department") or "Unknown" for j in co_jobs)
    top = dept_counts.most_common(top_n)
    if not top:
        return _empty_chart(f"No data for {_company_label(company_key)}")
    labels = [t[0] for t in reversed(top)]
    vals   = [t[1] for t in reversed(top)]
    color  = _company_color(company_key)
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker_color=color, marker_opacity=0.85,
        text=vals, textposition="outside",
        hovertemplate="%{y}: %{x} jobs<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=_company_label(company_key), font_size=13, x=0),
        height=max(300, 28 * len(top) + 60),
        margin=dict(t=36, b=20, l=200, r=50),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0", zeroline=False),
        yaxis=dict(showgrid=False),
    )
    return fig

def _chart_vertical_domains(jobs):
    companies = list(COMPANIES.keys())
    domain_keys = list(VERTICAL_DOMAINS.keys())
    counts = {dk: {co: 0 for co in companies} for dk in domain_keys}
    for j in jobs:
        for dk in json.loads(j.get("vertical_domains","[]")):
            if dk in counts: counts[dk][j["company"]] += 1
    active = [dk for dk in domain_keys if sum(counts[dk].values()) > 0]
    if not active: return _empty_chart("No vertical-domain jobs detected yet")
    fig = go.Figure()
    for co in companies:
        vals = [counts[dk][co] for dk in active]
        fig.add_trace(go.Bar(name=_company_label(co), x=[_dom_label(dk) for dk in active],
            y=vals, marker_color=_company_color(co), text=vals, textposition="outside"))
    fig.update_layout(barmode="group", xaxis_tickangle=-25,
        legend=dict(orientation="h", y=1.08, x=0),
        height=380, margin=dict(t=40,b=90,l=40,r=20),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"))
    return fig

def _chart_company_pie(jobs):
    cc = Counter(j["company"] for j in jobs)
    fig = go.Figure(go.Pie(
        labels=[_company_label(k) for k in cc], values=list(cc.values()),
        marker_colors=[_company_color(k) for k in cc],
        hole=0.52, textinfo="label+percent+value", textfont_size=13,
        hovertemplate="%{label}: %{value} jobs (%{percent})<extra></extra>"))
    fig.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
    return fig

def _chart_new_jobs_by_dept(new_jobs):
    """Two horizontal bars side-by-side, one per company, using native dept names."""
    from plotly.subplots import make_subplots
    companies = list(COMPANIES.keys())
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=[_company_label(co) for co in companies],
                        horizontal_spacing=0.12)
    for col_idx, co in enumerate(companies, start=1):
        co_jobs = [j for j in new_jobs if j["company"] == co]
        if not co_jobs:
            continue
        dept_counts = Counter(j.get("department") or "Unknown" for j in co_jobs)
        top = dept_counts.most_common(10)
        labels = [t[0] for t in reversed(top)]
        vals   = [t[1] for t in reversed(top)]
        fig.add_trace(go.Bar(
            x=vals, y=labels, orientation="h",
            marker_color=_company_color(co), showlegend=False,
            text=vals, textposition="outside",
            hovertemplate="%{y}: %{x}<extra></extra>",
        ), row=1, col=col_idx)
    fig.update_layout(
        height=max(280, 28 * 10 + 80),
        margin=dict(t=40, b=20, l=170, r=50),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=False)
    fig.update_yaxes(showgrid=False)
    return fig

def _chart_total_trend(snapshots):
    by_co = defaultdict(list); dates_co = defaultdict(list)
    for s in snapshots:
        co = s["company"]
        dates_co[co].append(s["snapshot_at"][:10])
        by_co[co].append(s["total_active"])
    fig = go.Figure()
    for co in COMPANIES:
        if co not in by_co: continue
        fig.add_trace(go.Scatter(x=dates_co[co], y=by_co[co], mode="lines+markers",
            name=_company_label(co), line=dict(color=_company_color(co), width=3),
            marker=dict(size=8, line=dict(width=2, color="white")),
            hovertemplate="%{x}: %{y} jobs<extra>" + _company_label(co) + "</extra>"))
    fig.update_layout(xaxis_title=None, yaxis_title="Active Listings",
        legend=dict(orientation="h", y=1.08, x=0),
        height=300, margin=dict(t=30,b=40,l=50,r=20),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"), hovermode="x unified")
    return fig

def _chart_category_trend(snapshots):
    """Separate department trend lines per company (stored in categories_json)."""
    from plotly.subplots import make_subplots
    companies = list(COMPANIES.keys())

    # Build {company: {date: {dept: count}}}
    co_date_dept: dict[str, dict[str, dict[str, int]]] = {co: defaultdict(dict) for co in companies}
    for s in snapshots:
        co = s["company"]
        dt = s["snapshot_at"][:10]
        co_date_dept[co][dt] = s["categories"]

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=[_company_label(co) for co in companies],
                        horizontal_spacing=0.10)
    for col_idx, co in enumerate(companies, start=1):
        date_dept = co_date_dept[co]
        dates_sorted = sorted(date_dept)
        if not dates_sorted:
            continue
        all_depts = {d for dt_data in date_dept.values() for d in dt_data}
        # Show top 8 departments by last-snapshot count
        top_depts = sorted(all_depts,
            key=lambda d: -date_dept[dates_sorted[-1]].get(d, 0))[:8]
        colors = ["#5C6BC0","#EF5350","#66BB6A","#FFA726","#26C6DA",
                  "#AB47BC","#8D6E63","#78909C"]
        for i, dept in enumerate(top_depts):
            fig.add_trace(go.Scatter(
                x=dates_sorted,
                y=[date_dept[dt].get(dept, 0) for dt in dates_sorted],
                mode="lines+markers", name=dept,
                legendgroup=co + dept,
                showlegend=(col_idx == 1),
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=6, line=dict(width=1, color="white")),
                hovertemplate="%{x}: %{y}<extra>" + dept + "</extra>",
            ), row=1, col=col_idx)

    fig.update_layout(
        xaxis_title=None, yaxis_title="Active",
        legend=dict(orientation="h", y=-0.22, x=0, font_size=10),
        height=380, margin=dict(t=40, b=110, l=50, r=20),
        plot_bgcolor="white", paper_bgcolor="white",
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig

def _chart_vertical_domain_trend(snapshots):
    date_dom = defaultdict(lambda: defaultdict(int)); all_domains = set()
    for s in snapshots:
        dt = s["snapshot_at"][:10]
        for dk, cnt in s["vertical_domains"].items():
            date_dom[dt][dk] += cnt; all_domains.add(dk)
    dates_sorted = sorted(date_dom)
    active = [d for d in all_domains
        if any(date_dom[dt].get(d,0) > 0 for dt in dates_sorted)]
    active.sort(key=lambda d: -sum(date_dom[dt].get(d,0) for dt in dates_sorted))
    if not active: return _empty_chart("No vertical-domain trend data yet")
    fig = go.Figure()
    for dk in active:
        fig.add_trace(go.Scatter(x=dates_sorted,
            y=[date_dom[dt].get(dk,0) for dt in dates_sorted],
            mode="lines+markers", name=_dom_label(dk),
            line=dict(color=_dom_color(dk), width=2),
            marker=dict(size=6, line=dict(width=1, color="white")),
            hovertemplate="%{x}: %{y}<extra>" + _dom_label(dk) + "</extra>"))
    fig.update_layout(xaxis_title=None, yaxis_title="Active Listings",
        legend=dict(orientation="h", y=-0.28, x=0, font_size=11),
        height=400, margin=dict(t=20,b=130,l=50,r=20),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"), hovermode="x unified")
    return fig

def _empty_chart(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, showarrow=False,
        font_size=14, font_color="#aaa")
    fig.update_layout(height=180, xaxis_visible=False, yaxis_visible=False,
        paper_bgcolor="white")
    return fig

# ── stats helper ───────────────────────────────────────────────────────────

def _build_stats(jobs):
    by_company = defaultdict(list)
    for j in jobs: by_company[j["company"]].append(j)
    domain_jobs = [j for j in jobs if json.loads(j.get("vertical_domains","[]"))]
    dom_counter = Counter()
    for j in domain_jobs:
        for dk in json.loads(j.get("vertical_domains","[]")): dom_counter[dk] += 1
    return {
        "total": len(jobs),
        "by_company": {k: len(v) for k, v in by_company.items()},
        "vertical_domain_jobs": len(domain_jobs),
        "domain_jobs_list": sorted(domain_jobs, key=lambda j: (j["company"], j.get("job_category",""))),
    }

def _prep_job(j):
    j = dict(j)
    raw = j.get("vertical_domains","[]")
    j["vertical_domains_list"] = json.loads(raw) if isinstance(raw, str) else (raw or [])
    return j

def _env():
    env = Environment(loader=BaseLoader(), autoescape=False)
    env.globals.update(cat_label=_cat_label, dom_label=_dom_label,
        company_label=_company_label, company_color=_company_color)
    return env

# ── public API ──────────────────────────────────────────────────────────────

def generate_report(all_jobs, run_type, snapshots=None,
                    new_jobs=None, since=None, removed_jobs=None):
    """
    Unified report generator.
    run_type:     'initial' | 'weekly'
    snapshots:    list from database.get_snapshots() (used for trend charts)
    new_jobs:     list of newly added job dicts (weekly only)
    removed_jobs: list of jobs that became inactive this run (weekly only)
    since:        human-readable string of last run time (weekly only)
    """
    from _template import TEMPLATE

    all_jobs = [_prep_job(j) for j in all_jobs]
    stats    = _build_stats(all_jobs)

    new_jobs = [_prep_job(j) for j in (new_jobs or [])]
    new_vertical_jobs = sorted(
        [j for j in new_jobs if j["vertical_domains_list"]],
        key=lambda j: j["company"],
    )

    removed_jobs = [_prep_job(j) for j in (removed_jobs or [])]
    removed_vertical_jobs = sorted(
        [j for j in removed_jobs if j["vertical_domains_list"]],
        key=lambda j: j["company"],
    )

    # ── current-snapshot charts (always first=True for one of them) ──
    first = True
    pie_html         = _fig_html(_chart_company_pie(all_jobs),                first=first); first=False
    anthropic_dept_html = _fig_html(_chart_dept_breakdown(all_jobs, "anthropic"), first=first)
    openai_dept_html    = _fig_html(_chart_dept_breakdown(all_jobs, "openai"),    first=first)
    domain_bar_html     = _fig_html(_chart_vertical_domains(all_jobs),            first=first)

    new_cat_html = ""
    if new_jobs:
        new_cat_html = _fig_html(_chart_new_jobs_by_dept(new_jobs), first=first)

    # ── trend charts (need >= 2 snapshots) ──
    # trend charts need >= 2 distinct dates
    unique_dates = len({s["snapshot_at"][:10] for s in snapshots}) if snapshots else 0
    has_trends   = unique_dates >= 2
    n_snapshots = len(snapshots) if snapshots else 0
    trend_total_html = trend_cat_html = trend_dom_html = ""
    if has_trends:
        trend_total_html = _fig_html(_chart_total_trend(snapshots),          first=first)
        trend_cat_html   = _fig_html(_chart_category_trend(snapshots),       first=first)
        trend_dom_html   = _fig_html(_chart_vertical_domain_trend(snapshots),first=first)

    tpl  = _env().from_string(TEMPLATE)
    html = tpl.render(
        generated_at=_ts(),
        run_type=run_type,
        since=since or "",
        stats=stats,
        pie_html=pie_html,
        anthropic_dept_html=anthropic_dept_html,
        openai_dept_html=openai_dept_html,
        domain_bar_html=domain_bar_html,
        new_jobs=new_jobs,
        new_vertical_jobs=new_vertical_jobs,
        new_total=len(new_jobs),
        new_vertical=len(new_vertical_jobs),
        new_cat_html=new_cat_html,
        removed_jobs=removed_jobs,
        removed_vertical_jobs=removed_vertical_jobs,
        removed_total=len(removed_jobs),
        removed_vertical=len(removed_vertical_jobs),
        has_trends=has_trends,
        n_snapshots=n_snapshots,
        unique_dates=unique_dates,
        trend_total_html=trend_total_html,
        trend_cat_html=trend_cat_html,
        trend_dom_html=trend_dom_html,
    )

    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = "weekly" if run_type == "weekly" else "initial"
    out = Path(REPORTS_DIR) / f"{tag}_report_{ts}.html"
    out.write_text(html, encoding="utf-8")
    logger.info("Report saved to %s", out)
    return str(out)


# ── backwards-compat shims (main.py calls these) ────────────────────────────

def generate_initial_report(jobs, snapshots=None):
    return generate_report(jobs, run_type="initial", snapshots=snapshots)

def generate_weekly_report(new_jobs, since, snapshots=None, all_jobs=None, removed_jobs=None):
    return generate_report(all_jobs or [], run_type="weekly",
                           snapshots=snapshots, new_jobs=new_jobs,
                           since=since, removed_jobs=removed_jobs)