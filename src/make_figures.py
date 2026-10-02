"""Figures for the README: run with `python -m src.make_figures`.

Reads the warehouse `run_pipeline.py` builds, so every number drawn here comes
from the same dbt models the marts expose. Run the pipeline first.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "mining_dw.duckdb"
FIG_DIR = ROOT / "outputs" / "figures"

INK = "#2B2B2B"
GRID = "#D9D9D9"
CLEAN = "#4C7A3E"
INCID = "#B5553D"
NEUTRAL = "#8FA8B8"
ORE = "#B58900"
RISK_COLOR = {"Bajo": "#4C7A3E", "Medio": "#B58900", "Alto": "#C2703D", "Crítico": "#A33F2B"}
RISK_ORDER = ["Bajo", "Medio", "Alto", "Crítico"]


def _style(ax, title=None, xlabel=None, ylabel=None, grid_axis="y"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK, labelsize=9)
    if title:
        ax.set_title(title, fontsize=11.5, color=INK, pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color=INK)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=INK)
    return ax


def _save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote outputs/figures/{name}")


# --------------------------------------------------------------------------
# 1. The whole point of unifying the three domains
# --------------------------------------------------------------------------
def figure_cross_domain(con):
    print("1/4 cross_domain_safety_oee ...")
    df = con.execute("""
        select case when total_incidentes = 0 then 'clean' else 'incident' end as grp,
               count(*) as n,
               avg(tiee_pct) as tiee, avg(desempeno_pct) as desemp,
               avg(calidad_pct) as calidad, avg(oee_pct) as oee,
               avg(recuperacion_cu_pct) as recup
        from fct_daily_mining_kpis group by 1
    """).fetchdf().set_index("grp")
    clean, inc = df.loc["clean"], df.loc["incident"]

    oee = con.execute("""
        select case when total_incidentes = 0 then 'clean' else 'incident' end as grp, oee_pct
        from fct_daily_mining_kpis
    """).fetchdf()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5),
                                   gridspec_kw={"width_ratios": [1.1, 1]})

    factors = ["tiee", "desemp", "calidad", "oee"]
    labels = ["Availability\n(TIEE)", "Performance", "Quality\n(from safety)", "OEE\n(the product)"]
    x = np.arange(len(factors))
    vc = [clean[f] for f in factors]
    vi = [inc[f] for f in factors]
    ax1.bar(x - 0.19, vc, width=0.38, color=CLEAN, edgecolor="white", linewidth=1.1,
            label=f"No safety incident (n={int(clean['n'])})")
    ax1.bar(x + 0.19, vi, width=0.38, color=INCID, edgecolor="white", linewidth=1.1,
            label=f"Safety incident (n={int(inc['n'])})")
    for i, (a, b) in enumerate(zip(vc, vi)):
        ax1.text(i - 0.19, a + 1.2, f"{a:.1f}", ha="center", fontsize=8.6, color=INK)
        ax1.text(i + 0.19, b + 1.2, f"{b:.1f}", ha="center", fontsize=8.6, color=INCID,
                 fontweight="bold")
        material = abs(b - a) > 1
        ax1.text(i, max(a, b) + 6.5, f"{b - a:+.2f} pp", ha="center", fontsize=8.6,
                 color=INCID if material else "#8A8A8A",
                 fontweight="bold" if material else "normal")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylim(0, 122)
    _style(ax1, ylabel="Shift average (%)")
    ax1.set_title("The OEE gap flows through Quality alone",
                  fontsize=11.5, color=INK, pad=12)
    ax1.legend(frameon=False, fontsize=8.8, loc="upper center", ncol=2)

    bins = np.linspace(oee["oee_pct"].min(), oee["oee_pct"].max(), 34)
    ax2.hist(oee.loc[oee.grp == "clean", "oee_pct"], bins=bins, color=CLEAN, alpha=0.62,
             label="No incident")
    ax2.hist(oee.loc[oee.grp == "incident", "oee_pct"], bins=bins, color=INCID, alpha=0.62,
             label="Incident")
    ax2.axvline(clean["oee"], color=CLEAN, linestyle="--", linewidth=1.4)
    ax2.axvline(inc["oee"], color=INCID, linestyle="--", linewidth=1.4)
    _style(ax2, xlabel="OEE (%)", ylabel="Shifts")
    ax2.set_title(f"Distributions overlap heavily\nmeans {inc['oee']:.2f} vs {clean['oee']:.2f}",
                  fontsize=11.5, color=INK, pad=12)
    ax2.legend(frameon=False, fontsize=8.8)

    fig.text(0.5, -0.085,
             "540 shifts (3 sites x 90 days x 2 shifts). This is the cross-domain link working as "
             "designed, not an empirical discovery:\n"
             "OEE's Quality factor is defined as 1 - safety_downtime / shift_hours, so a shift with "
             "an incident must score lower.\nWhat the chart adds is that the effect is confined to "
             f"that factor — availability moves {inc['tiee'] - clean['tiee']:+.2f} pp and performance "
             f"{inc['desemp'] - clean['desemp']:+.2f} pp, both noise —\nand that copper recovery moves "
             f"{inc['recup'] - clean['recup']:+.2f} pp, because the flotation domain is joined at the "
             "same grain but not wired into this formula.",
             ha="center", fontsize=8.5, color="#666666")
    _save(fig, "cross_domain_safety_oee.png")
    return clean, inc


# --------------------------------------------------------------------------
# 2. The two headline KPI distributions
# --------------------------------------------------------------------------
def figure_kpi_distributions(con):
    print("2/4 kpi_distributions ...")
    df = con.execute("""
        select oee_pct, recuperacion_cu_pct, tiee_pct, desempeno_pct
        from fct_daily_mining_kpis
    """).fetchdf()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 4.6))

    for ax, col, color, name, bound in (
        (ax1, "oee_pct", NEUTRAL, "OEE", 100),
        (ax2, "recuperacion_cu_pct", ORE, "Copper recovery", None),
    ):
        v = df[col]
        ax.hist(v, bins=36, color=color, edgecolor="white", linewidth=0.6)
        ax.axvline(v.mean(), color=INK, linestyle="--", linewidth=1.3)
        ax.text(v.mean(), ax.get_ylim()[1] * 0.94, f" mean {v.mean():.2f}%",
                fontsize=9, color=INK)
        _style(ax, xlabel=f"{name} (%)", ylabel="Shifts")
        ax.set_title(f"{name} — {v.min():.2f}% to {v.max():.2f}%", fontsize=11, color=INK, pad=10)
        if bound:
            ax.axvline(bound, color=INCID, linestyle=":", linewidth=1.2)
            ax.text(bound - 0.6, ax.get_ylim()[1] * 0.6, "100% ceiling", fontsize=8.2,
                    color=INCID, rotation=90, va="top", ha="right")

    o, r = df["oee_pct"], df["recuperacion_cu_pct"]
    fig.text(0.5, -0.07,
             f"OEE spans {o.max() - o.min():.1f} points across shifts and never exceeds 100%, which is "
             "the arithmetic sanity check for a product of three bounded factors.\n"
             f"Recovery spans only {r.max() - r.min():.1f} points and sits in the 81-86% band that is "
             "realistic for copper flotation — it is computed with the standard\ntwo-product formula "
             "R = c(f-t) / f(c-t) x 100, not a project-invented one, which is why its range is the "
             "more meaningful of the two.",
             ha="center", fontsize=8.5, color="#666666")
    _save(fig, "kpi_distributions.png")
    return df


# --------------------------------------------------------------------------
# 3. The risk level, and what this dataset never exercises
# --------------------------------------------------------------------------
def figure_risk(con):
    print("3/4 risk_distribution ...")
    df = con.execute("""
        select nivel_riesgo, puntaje_riesgo_operacional as score, count(*) as n,
               max(total_incidentes) as max_inc, avg(oee_pct) as oee
        from fct_daily_mining_kpis group by 1, 2 order by score
    """).fetchdf()
    max_inc_overall = int(con.execute(
        "select max(total_incidentes) from fct_daily_mining_kpis").fetchone()[0])
    n_scores = int(con.execute(
        "select count(distinct puntaje_riesgo_operacional) from fct_daily_mining_kpis").fetchone()[0])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 4.7))

    order = [l for l in RISK_ORDER if l in set(df["nivel_riesgo"])]
    counts = [int(df.loc[df.nivel_riesgo == l, "n"].iloc[0]) for l in order]
    scores = [int(df.loc[df.nivel_riesgo == l, "score"].iloc[0]) for l in order]
    bars = ax1.bar(order, counts, color=[RISK_COLOR[l] for l in order], width=0.62,
                   edgecolor="white", linewidth=1.2)
    total = sum(counts)
    for b, c, s in zip(bars, counts, scores):
        ax1.text(b.get_x() + b.get_width() / 2, c + 6, f"{c}\n{c / total:.0%}",
                 ha="center", fontsize=9, color=INK)
        ax1.text(b.get_x() + b.get_width() / 2, 6, f"score {s}", ha="center",
                 fontsize=8.2, color="white" if c > 40 else INK)
    _style(ax1, ylabel="Shifts")
    ax1.set_ylim(0, max(counts) * 1.26)
    ax1.set_title(f"Operational risk across {total} shifts", fontsize=11, color=INK, pad=12)

    oees = [float(df.loc[df.nivel_riesgo == l, "oee"].iloc[0]) for l in order]
    ax2.plot(order, oees, color=INK, linewidth=1.4, marker="o", markersize=9,
             markerfacecolor="white", markeredgewidth=1.8, zorder=3)
    for i, (l, v) in enumerate(zip(order, oees)):
        ax2.scatter([i], [v], s=90, color=RISK_COLOR[l], zorder=4, edgecolor="white", linewidth=1.5)
        ax2.text(i, v + 0.32, f"{v:.2f}", ha="center", fontsize=9, color=INK)
    ax2.set_xlim(-0.35, len(order) - 0.55)
    _style(ax2, ylabel="Mean OEE (%)")
    ax2.set_title(f"Mean OEE by risk level — {oees[0] - oees[-1]:.1f} points "
                  f"from {order[0]} to {order[-1]}", fontsize=11, color=INK, pad=12)

    fig.text(0.5, -0.115,
             f"The score is sum(LEVE=1, GRAVE=5, FATAL=25) over a shift's incidents, and the level "
             f"thresholds (0 / <5 / <25 / else) are built to let\nseveral mild incidents accumulate "
             "into a serious level — five LEVE incidents would score 5 and read Alto.\n"
             f"That path is never exercised here: no shift in this run has more than "
             f"{max_inc_overall} incident, so the score takes only {n_scores} distinct values and "
             "`nivel_riesgo`\ncollapses into a relabelling of that single incident's severity. The "
             "formula is built for accumulation; this synthetic data does not test it.",
             ha="center", fontsize=8.5, color="#666666")
    _save(fig, "risk_distribution.png")
    return order, counts, scores, max_inc_overall, n_scores


# --------------------------------------------------------------------------
# 4. Are the ML views actually trainable?
# --------------------------------------------------------------------------
def figure_ml_views(con):
    print("4/4 ml_view_readiness ...")
    pdm = con.execute("""
        select count(*) as rows,
               count(falla_siguiente_turno) as labelled,
               sum(case when falla_siguiente_turno then 1 else 0 end) as positives
        from ml_predictive_maintenance
    """).fetchdf().iloc[0]
    ore = con.execute("""
        select count(*) as rows,
               count(target_recuperacion_cu_pct) as labelled,
               count(target_ley_concentrado_cu_pct) as labelled_grade
        from ml_ore_grade_prediction
    """).fetchdf().iloc[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 4.6),
                                   gridspec_kw={"width_ratios": [1, 1.1]})

    names = ["ml_predictive\n_maintenance", "ml_ore_grade\n_prediction"]
    totals = [int(pdm["rows"]), int(ore["rows"])]
    labelled = [int(pdm["labelled"]), int(ore["labelled"])]
    x = np.arange(2)
    ax1.bar(x, totals, width=0.52, color=NEUTRAL, edgecolor="white", linewidth=1.2, label="Rows")
    ax1.bar(x, labelled, width=0.52, color=CLEAN, edgecolor="white", linewidth=1.2,
            label="With a non-null target")
    for i, (t, l) in enumerate(zip(totals, labelled)):
        ax1.text(i, t + 110, f"{t:,} rows", ha="center", fontsize=9, color=INK)
        ax1.text(i, l / 2, f"{l:,}\n{l / t:.1%}", ha="center", va="center", fontsize=9,
                 color="white", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, fontsize=9)
    ax1.set_ylim(0, max(totals) * 1.16)
    _style(ax1, ylabel="Rows")
    ax1.set_title("Label coverage of the ML-ready views", fontsize=11, color=INK, pad=12)
    ax1.legend(frameon=False, fontsize=8.6)

    pos = int(pdm["positives"])
    neg = int(pdm["labelled"]) - pos
    ax2.barh([0], [neg], color=NEUTRAL, height=0.5, edgecolor="white", linewidth=1.2,
             label=f"No failure next shift ({neg:,})")
    ax2.barh([0], [pos], left=[neg], color=INCID, height=0.5, edgecolor="white", linewidth=1.2,
             label=f"Failure next shift ({pos:,})")
    ax2.text(neg / 2, 0, f"{neg / (neg + pos):.1%}", ha="center", va="center", fontsize=10,
             color="white", fontweight="bold")
    ax2.text(neg + pos / 2, 0, f"{pos / (neg + pos):.1%}", ha="center", va="center", fontsize=9,
             color="white", fontweight="bold")
    ax2.set_yticks([])
    ax2.set_xlim(0, neg + pos)
    _style(ax2, xlabel="Labelled rows", grid_axis="x")
    ax2.set_title(f"`falla_siguiente_turno` is imbalanced "
                  f"({(neg + pos) / pos:.1f}:1)", fontsize=11, color=INK, pad=12)
    ax2.legend(frameon=False, fontsize=8.6, loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=2)

    unlabelled = totals[0] - labelled[0]
    fig.text(0.5, -0.145,
             f"Both views expose an explicit target column, so a model trains against them with no "
             "separate feature-engineering step.\n"
             f"The {unlabelled} unlabelled maintenance rows are the last observed shift of each truck, "
             "where there is no next shift to label — expected, not missing data.\n"
             f"The class balance is worth seeing before training: at {pos / (neg + pos):.1%} positives, "
             "accuracy is a useless metric here and the view\nis honest about it by exposing the raw "
             "flag rather than a pre-balanced sample.",
             ha="center", fontsize=8.5, color="#666666")
    _save(fig, "ml_view_readiness.png")
    return pdm, ore


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit(f"No warehouse at {DB_PATH}. Run `python run_pipeline.py` first.")
    print(f"Reading {DB_PATH}\nWriting figures to {FIG_DIR}\n")
    con = duckdb.connect(str(DB_PATH), read_only=True)

    clean, inc = figure_cross_domain(con)
    kpis = figure_kpi_distributions(con)
    order, counts, scores, max_inc, n_scores = figure_risk(con)
    pdm, ore = figure_ml_views(con)

    print("\nNumbers annotated on the figures:")
    print(f"  shifts            : {int(clean['n']) + int(inc['n'])} "
          f"({int(inc['n'])} with a safety incident)")
    print(f"  OEE clean/incident: {clean['oee']:.2f} / {inc['oee']:.2f} "
          f"({inc['oee'] - clean['oee']:+.2f} pp)")
    print(f"  quality factor    : {clean['calidad']:.2f} / {inc['calidad']:.2f} "
          f"({inc['calidad'] - clean['calidad']:+.2f} pp)")
    print(f"  availability      : {clean['tiee']:.2f} / {inc['tiee']:.2f} "
          f"({inc['tiee'] - clean['tiee']:+.2f} pp)")
    print(f"  OEE range         : {kpis['oee_pct'].min():.2f} - {kpis['oee_pct'].max():.2f} "
          f"(avg {kpis['oee_pct'].mean():.2f})")
    print(f"  recovery range    : {kpis['recuperacion_cu_pct'].min():.2f} - "
          f"{kpis['recuperacion_cu_pct'].max():.2f} (avg {kpis['recuperacion_cu_pct'].mean():.2f})")
    print(f"  risk              : {dict(zip(order, counts))}, scores {scores}")
    print(f"  risk degeneracy   : max {max_inc} incident/shift, {n_scores} distinct scores")
    print(f"  ml_pdm labels     : {int(pdm['labelled'])}/{int(pdm['rows'])}, "
          f"{int(pdm['positives'])} positives")
    print(f"  ml_ore labels     : {int(ore['labelled'])}/{int(ore['rows'])}")
