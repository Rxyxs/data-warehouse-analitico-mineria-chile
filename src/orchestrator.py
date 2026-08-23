"""Orquestador del pipeline completo: ingesta -> dbt seed -> dbt run -> dbt test,
en un solo comando, sin intervención humana.

Ejecutar desde la raíz del repositorio con:
    python -m src.orchestrator
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = ROOT_DIR / "dbt_project"

# Se resuelve el binario de dbt junto al interprete actual (mismo venv/Scripts o
# bin) en vez de depender de que el venv este activado en la shell y `dbt` este
# en el PATH.
_DBT_BIN_NAME = "dbt.exe" if sys.platform == "win32" else "dbt"
DBT_BIN = str(Path(sys.executable).with_name(_DBT_BIN_NAME))


def _run_step(description: str, cmd: list[str]) -> None:
    print(f"\n{'=' * 70}\n>> {description}\n{'=' * 70}")
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"\n[ERROR] Paso fallido: {description} (código {result.returncode})")
        sys.exit(result.returncode)


def main() -> None:
    dbt_common_args = ["--project-dir", str(DBT_PROJECT_DIR), "--profiles-dir", str(DBT_PROJECT_DIR)]

    _run_step("1/4 Ingesta de datos crudos -> DuckDB", [sys.executable, "-m", "src.ingest"])
    _run_step("2/4 dbt seed (dimensión de equipos CAEX)", [DBT_BIN, "seed", *dbt_common_args])
    _run_step("3/4 dbt run (staging -> intermediate -> marts)", [DBT_BIN, "run", *dbt_common_args])
    _run_step("4/4 dbt test (tests genéricos + custom)", [DBT_BIN, "test", *dbt_common_args])

    print("\nPipeline completo. Base de datos lista en data/mining_dw.duckdb")


if __name__ == "__main__":
    main()
