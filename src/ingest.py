"""Genera datos operacionales sintéticos de los 3 dominios (flotación, mantención CAEX,
seguridad) y los carga como tablas raw en un DuckDB local.

Los datos son 100% sintéticos, generados con una semilla fija para reproducibilidad.
Los nombres de faena (Andina, Los Bronces, El Teniente) y modelos de camión CAEX
(Caterpillar 797F, Komatsu 930E, Liebherr T284) se usan solo como color realista del
dominio minero chileno -- ninguna cifra representa operación real de esas faenas.

Ejecutar desde la raíz del repositorio con:
    python -m src.ingest
"""

from __future__ import annotations

import datetime as dt
import random
from pathlib import Path

import duckdb
import polars as pl

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "mining_dw.duckdb"

SEED = 42
N_DAYS = 90
END_DATE = dt.date.today()
START_DATE = END_DATE - dt.timedelta(days=N_DAYS - 1)

FAENAS = ["Andina", "Los Bronces", "El Teniente"]
TURNOS = ["Día", "Noche"]
HORAS_TURNO_PROGRAMADAS = 12.0

CAMIONES = {
    "Andina": ["CAEX-101", "CAEX-102", "CAEX-103"],
    "Los Bronces": ["CAEX-201", "CAEX-202", "CAEX-203"],
    "El Teniente": ["CAEX-301", "CAEX-302", "CAEX-303"],
}

INCIDENT_TYPES = [
    "atrapamiento_chancador",
    "caida_roca_frente_avance",
    "atropello_caex",
    "falla_fortificacion",
    "exposicion_gases",
    "caida_altura",
    "incendio_equipo",
    "colision_vehicular",
]

SEVERITY_WEIGHTS = {"LEVE": 0.60, "GRAVE": 0.33, "FATAL": 0.07}


def _turno_from_hour(hour: int) -> str:
    return "Día" if 8 <= hour < 20 else "Noche"


def _daterange(start: dt.date, end: dt.date):
    for i in range((end - start).days + 1):
        yield start + dt.timedelta(days=i)


def generate_flotation_telemetry(rng: random.Random) -> pl.DataFrame:
    """Telemetría horaria de planta de flotación por faena (~6480 filas)."""
    rows = []
    record_id = 1
    for faena in FAENAS:
        for fecha in _daterange(START_DATE, END_DATE):
            for hour in range(24):
                ts = dt.datetime.combine(fecha, dt.time(hour=hour))
                ley_alimentacion = max(0.35, rng.gauss(0.70, 0.08))
                ley_cola = ley_alimentacion * rng.uniform(0.12, 0.22)
                ley_concentrado = min(36.0, max(24.0, rng.gauss(30.0, 2.0)))
                tonelaje_hora = max(50.0, rng.gauss(320.0, 35.0))
                rows.append(
                    {
                        "record_id": record_id,
                        "faena": faena,
                        "ts": ts,
                        "turno": _turno_from_hour(hour),
                        "tonelaje_hora_ton": round(tonelaje_hora, 2),
                        "ley_alimentacion_cu_pct": round(ley_alimentacion, 4),
                        "ley_concentrado_cu_pct": round(ley_concentrado, 4),
                        "ley_cola_cu_pct": round(ley_cola, 4),
                        "dosis_reactivo_gpt": round(max(5.0, rng.gauss(38.0, 8.0)), 2),
                        "ph_pulpa": round(min(12.0, max(8.0, rng.gauss(10.2, 0.4))), 2),
                    }
                )
                record_id += 1
    return pl.DataFrame(rows)


def generate_caex_maintenance(rng: random.Random) -> pl.DataFrame:
    """Registro de mantención/operación CAEX por camión, día y turno (~3240 filas)."""
    rows = []
    record_id = 1
    for faena in FAENAS:
        for camion_id in CAMIONES[faena]:
            for fecha in _daterange(START_DATE, END_DATE):
                for turno in TURNOS:
                    mantencion_programada = 0.0
                    if rng.random() < 0.15:
                        mantencion_programada = rng.uniform(1.5, 6.0)
                    falla_no_programada = 0.0
                    if rng.random() < 0.08:
                        falla_no_programada = rng.uniform(0.5, 4.0)
                    espera_operacional = rng.uniform(0.0, 1.0)
                    horas_operativas = max(
                        0.0,
                        HORAS_TURNO_PROGRAMADAS
                        - mantencion_programada
                        - falla_no_programada
                        - espera_operacional,
                    )
                    # Media por debajo del minimo ciclos_hora_nominal de la flota (2.0,
                    # ver seeds/dim_equipos_caex.csv) para que el desempeno real rara vez
                    # supere el nominal -- igual se acota en int_equipment_performance.sql
                    # por si un camion de nominal alto tiene una racha de ciclos rapidos.
                    ciclos_hora_real = rng.gauss(1.85, 0.18)
                    num_ciclos = max(0.0, horas_operativas * ciclos_hora_real)
                    fill_factor = rng.uniform(0.85, 1.05)
                    rows.append(
                        {
                            "record_id": record_id,
                            "faena": faena,
                            "camion_id": camion_id,
                            "fecha": fecha,
                            "turno": turno,
                            "horas_turno_programadas": HORAS_TURNO_PROGRAMADAS,
                            "horas_operativas": round(horas_operativas, 2),
                            "horas_mantencion_programada": round(mantencion_programada, 2),
                            "horas_falla_no_programada": round(falla_no_programada, 2),
                            "num_ciclos": round(num_ciclos, 1),
                            "fill_factor": round(fill_factor, 3),
                        }
                    )
                    record_id += 1
    return pl.DataFrame(rows)


def generate_safety_incidents(rng: random.Random) -> pl.DataFrame:
    """Incidentes de seguridad por faena, día y turno (~esperado ~200 filas)."""
    rows = []
    incident_id = 1
    severities = list(SEVERITY_WEIGHTS.keys())
    weights = list(SEVERITY_WEIGHTS.values())
    for faena in FAENAS:
        for fecha in _daterange(START_DATE, END_DATE):
            for turno in TURNOS:
                if rng.random() >= 0.38:
                    continue
                severidad = rng.choices(severities, weights=weights, k=1)[0]
                if severidad == "LEVE":
                    horas_detencion = round(rng.uniform(0.0, 0.5), 2)
                elif severidad == "GRAVE":
                    horas_detencion = round(rng.uniform(1.0, 4.0), 2)
                else:
                    horas_detencion = round(rng.uniform(4.0, 12.0), 2)
                camion_id = rng.choice(CAMIONES[faena]) if rng.random() < 0.5 else None
                rows.append(
                    {
                        "incident_id": incident_id,
                        "faena": faena,
                        "fecha": fecha,
                        "turno": turno,
                        "camion_id": camion_id,
                        "severidad": severidad,
                        "tipo_incidente": rng.choice(INCIDENT_TYPES),
                        "horas_detencion_asociadas": horas_detencion,
                    }
                )
                incident_id += 1
    return pl.DataFrame(rows)


def build_database(db_path: Path = DB_PATH) -> dict[str, int]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    rng = random.Random(SEED)
    flotation_df = generate_flotation_telemetry(rng)
    maintenance_df = generate_caex_maintenance(rng)
    safety_df = generate_safety_incidents(rng)

    con = duckdb.connect(str(db_path))
    try:
        con.register("flotation_view", flotation_df.to_arrow())
        con.execute("CREATE OR REPLACE TABLE raw_flotation_telemetry AS SELECT * FROM flotation_view")

        con.register("maintenance_view", maintenance_df.to_arrow())
        con.execute("CREATE OR REPLACE TABLE raw_caex_maintenance AS SELECT * FROM maintenance_view")

        con.register("safety_view", safety_df.to_arrow())
        con.execute("CREATE OR REPLACE TABLE raw_safety_incidents AS SELECT * FROM safety_view")
    finally:
        con.close()

    return {
        "raw_flotation_telemetry": len(flotation_df),
        "raw_caex_maintenance": len(maintenance_df),
        "raw_safety_incidents": len(safety_df),
    }


def main() -> None:
    counts = build_database()
    print(f"Base de datos creada en: {DB_PATH}")
    for table, n in counts.items():
        print(f"  {table}: {n} filas")


if __name__ == "__main__":
    main()
