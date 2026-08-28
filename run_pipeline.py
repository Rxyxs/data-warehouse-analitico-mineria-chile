"""Orquestador de nivel repositorio: ingesta -> dbt deps/seed/run -> **validación
de esquema en DuckDB** -> dbt test, en un solo comando.

Reutiliza los pasos de `src.orchestrator` (que sigue siendo un building block
independiente, útil por sí solo para quien solo quiera correr dbt) y agrega el
paso que ese módulo no tiene: una validación de esquema explícita contra
DuckDB, vía `information_schema`, distinta de `dbt test` -- `dbt test` valida
*calidad de datos* (rangos, nulos, unicidad); este paso valida que el
*contrato de esquema* (qué tablas/vistas existen, con qué columnas) es el que
el resto del proyecto espera, **antes** de correr las pruebas de calidad sobre
un esquema que podría estar incompleto por una razón distinta a un bug de
datos (p. ej. un modelo que no compiló, o un rename no propagado).

Ejecutar desde la raíz del repositorio con:
    python run_pipeline.py
    python run_pipeline.py --target postgres
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import duckdb

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.orchestrator import DBT_CMD, DBT_PROJECT_DIR, _run_step  # noqa: E402

DB_PATH = ROOT_DIR / "data" / "mining_dw.duckdb"

# Contrato de esquema esperado: tabla/vista -> columnas que deben existir.
# No es una copia de los tests de calidad de dbt (que viven en los schema.yml
# junto a cada modelo) -- es una lista deliberadamente corta de lo que un
# consumidor externo (el dashboard, un notebook de ML) asume que existe,
# mantenida a mano en este script de orquestación, no generada desde dbt.
SCHEMA_CONTRACT: dict[str, list[str]] = {
    "stg_flotation": ["record_id", "faena", "ts", "ley_alimentacion_cu_pct"],
    "stg_maintenance": ["record_id", "camion_id", "fecha", "turno", "horas_operativas"],
    "stg_safety": ["incident_id", "faena", "fecha", "severidad"],
    "int_equipment_performance": ["camion_id", "fecha", "turno", "disponibilidad_pct", "desempeno_pct"],
    "fct_daily_mining_kpis": [
        "fecha", "turno", "faena", "tiee_pct", "oee_pct", "recuperacion_cu_pct", "nivel_riesgo",
    ],
    "ml_predictive_maintenance": [
        "camion_id", "fecha", "turno", "disponibilidad_rolling_7t",
        "turnos_desde_ultima_falla", "falla_no_programada_flag", "falla_siguiente_turno",
    ],
    "ml_ore_grade_prediction": [
        "faena", "ts", "ley_alimentacion_cu_pct", "dosis_reactivo_rolling_6h",
        "target_ley_concentrado_cu_pct", "target_recuperacion_cu_pct",
    ],
}


def validate_duckdb_schema(db_path: Path = DB_PATH, contract: dict[str, list[str]] = SCHEMA_CONTRACT) -> None:
    """Falla ruidosamente (con el detalle exacto de qué falta) si alguna
    tabla/vista o columna del contrato de esquema no existe en la base --
    en vez de dejar que un consumidor aguas abajo (el dashboard, un notebook)
    falle mucho más tarde con un error de SQL menos legible."""
    if not db_path.exists():
        raise FileNotFoundError(
            f"No se encontró {db_path}. Corre primero la ingesta (paso 1) antes de validar el esquema."
        )

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        existing_tables = {
            row[0] for row in con.execute(
                "select table_name from information_schema.tables where table_schema = 'main'"
            ).fetchall()
        }

        errors: list[str] = []
        for table, expected_columns in contract.items():
            if table not in existing_tables:
                errors.append(f"  - falta la tabla/vista '{table}' (¿corrió 'dbt run'?)")
                continue

            existing_columns = {
                row[0] for row in con.execute(
                    "select column_name from information_schema.columns "
                    "where table_schema = 'main' and table_name = ?",
                    [table],
                ).fetchall()
            }
            missing = [c for c in expected_columns if c not in existing_columns]
            if missing:
                errors.append(f"  - '{table}' no tiene las columnas esperadas: {', '.join(missing)}")

        if errors:
            raise RuntimeError(
                "Validación de esquema DuckDB fallida:\n" + "\n".join(errors)
            )

        print(f"Esquema DuckDB validado: {len(contract)} tablas/vistas, "
              f"{sum(len(c) for c in contract.values())} columnas esperadas, todas presentes.")
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default="dev",
        help="Target de dbt: 'dev' (DuckDB local, por defecto) o 'postgres'.",
    )
    args = parser.parse_args()

    dbt_common_args = [
        "--project-dir", str(DBT_PROJECT_DIR), "--profiles-dir", str(DBT_PROJECT_DIR),
        "--target", args.target,
    ]

    _run_step("1/6 Ingesta de datos crudos -> DuckDB", [sys.executable, "-m", "src.ingest"])
    _run_step("2/6 dbt deps (instala dbt_utils)", [*DBT_CMD, "deps", *dbt_common_args])
    _run_step("3/6 dbt seed (dimensión de equipos CAEX)", [*DBT_CMD, "seed", *dbt_common_args])
    _run_step("4/6 dbt run (staging -> intermediate -> marts -> ml)", [*DBT_CMD, "run", *dbt_common_args])

    print(f"\n{'=' * 70}\n>> 5/6 Validación de esquema en DuckDB\n{'=' * 70}")
    if args.target == "dev":
        validate_duckdb_schema()
    else:
        print("  (omitida: la validación de esquema de este script asume DuckDB; "
              "para 'postgres' valida el esquema con las herramientas de esa base)")

    _run_step("6/6 dbt test (genéricos + dbt_utils + custom)", [*DBT_CMD, "test", *dbt_common_args])

    print(f"\nPipeline completo (target={args.target}).")
    if args.target == "dev":
        print(f"Base de datos lista en {DB_PATH}")


if __name__ == "__main__":
    main()
