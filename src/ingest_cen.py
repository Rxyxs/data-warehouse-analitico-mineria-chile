"""Ingesta de datos reales: costo marginal horario del SEN por barra (Coordinador Eléctrico Nacional).

El costo marginal horario de seis barras de 220 kV (Crucero, Cardones, Pan de Azúcar, Quillota,
Charrúa y Puerto Montt) se lee de los gráficos vectoriales de los informes diarios públicos del
Coordinador en el repositorio Rxyxs/chile-energy-grid-forecasting (``src/data/cen_daily_reports.py``,
2022-2025). Este módulo lo resume a una fila por día y barra (promedio del día, de las horas
solares 10-16 y de la noche 20-06, hora local) y la carga en DuckDB como ``raw_cen_cmg_diario``.

La tabla diaria se versiona en ``data/real/cen_cmg_diario_barra.csv``; ``--refresh`` la regenera
desde la serie horaria publicada en ese repositorio.

    python -m src.ingest_cen            # carga la tabla versionada en DuckDB
    python -m src.ingest_cen --refresh  # vuelve a resumir la serie horaria publicada
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "mining_dw.duckdb"
DAILY_CSV = ROOT_DIR / "data" / "real" / "cen_cmg_diario_barra.csv"
HOURLY_URL = ("https://raw.githubusercontent.com/Rxyxs/chile-energy-grid-forecasting/main/"
              "data/real/cen_cmg_hourly.csv.gz")
SOLAR_HOURS = range(10, 17)               # 10:00-16:59, hora local
NIGHT_HOURS = (*range(20, 24), *range(0, 7))  # 20:00-06:59


def daily_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    """Serie horaria (date, hour 1-24, bar, cmg_usd_mwh) -> una fila por día y barra.

    La hora h del informe es el bloque que empieza a las h-1 hora local."""
    # Los valores apenas bajo cero (-0,1 a -0,2) son ruido de la reconstrucción alrededor de un
    # costo marginal nulo (excedente solar del norte); el costo marginal del SEN no es negativo.
    h = hourly.assign(hora_local=hourly["hour"] - 1, cmg_usd_mwh=hourly["cmg_usd_mwh"].clip(lower=0))
    g = h.groupby(["date", "bar"])
    out = pd.DataFrame({
        "cmg_promedio_usd_mwh": g["cmg_usd_mwh"].mean(),
        "cmg_horas_solares_usd_mwh": h[h["hora_local"].isin(SOLAR_HOURS)].groupby(["date", "bar"])["cmg_usd_mwh"].mean(),
        "cmg_noche_usd_mwh": h[h["hora_local"].isin(NIGHT_HOURS)].groupby(["date", "bar"])["cmg_usd_mwh"].mean(),
        "horas": g["cmg_usd_mwh"].size(),
    }).reset_index().rename(columns={"date": "fecha", "bar": "barra"})
    return out.round(2).sort_values(["fecha", "barra"]).reset_index(drop=True)


def refresh() -> pd.DataFrame:
    hourly = pd.read_csv(HOURLY_URL)
    daily = daily_summary(hourly)
    DAILY_CSV.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(DAILY_CSV, index=False)
    return daily


def load(db_path: Path = DB_PATH, csv_path: Path = DAILY_CSV) -> int:
    df = pd.read_csv(csv_path, parse_dates=["fecha"])
    with duckdb.connect(str(db_path)) as con:
        con.execute("create or replace table raw_cen_cmg_diario as select * from df")
        return con.execute("select count(*) from raw_cen_cmg_diario").fetchone()[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="regenerar la tabla diaria desde la serie horaria")
    args = parser.parse_args()
    if args.refresh:
        d = refresh()
        print(f"{len(d):,} filas día-barra, {d['fecha'].nunique():,} días -> {DAILY_CSV}")
    n = load()
    print(f"raw_cen_cmg_diario: {n:,} filas en {DB_PATH}")
