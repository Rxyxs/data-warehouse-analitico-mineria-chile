"""Orquestador del pipeline completo: ingesta -> dbt seed -> dbt run -> dbt test,
en un solo comando, sin intervención humana.

Ejecutar desde la raíz del repositorio con:
    python -m src.orchestrator
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = ROOT_DIR / "dbt_project"

# Se invoca dbt como `python -m dbt.cli.main` (mismo interprete que este
# script, via sys.executable) en vez de resolver un binario `dbt`/`dbt.exe`
# separado en PATH o junto al interprete: el script de consola generado por
# pip para `dbt.exe` hornea la ruta del interprete usado al momento de la
# instalacion, y si esa ruta deja de coincidir con el venv activo (p.ej. tras
# mover o reubicar el proyecto) el binario se rompe de forma confusa aunque
# `import dbt` funcione perfectamente desde Python. Invocar el modulo
# directamente elimina esa clase entera de problema.
DBT_CMD = [sys.executable, "-m", "dbt.cli.main"]


def _run_step(description: str, cmd: list[str]) -> None:
    print(f"\n{'=' * 70}\n>> {description}\n{'=' * 70}")
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"\n[ERROR] Paso fallido: {description} (código {result.returncode})")
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default="dev",
        help="Target de dbt a usar (ver dbt_project/profiles.yml): 'dev' (DuckDB local, "
        "por defecto) o 'postgres' (requiere un servidor Postgres accesible via las "
        "variables de entorno MINING_DW_PG_*).",
    )
    args = parser.parse_args()

    dbt_common_args = [
        "--project-dir", str(DBT_PROJECT_DIR), "--profiles-dir", str(DBT_PROJECT_DIR),
        "--target", args.target,
    ]

    _run_step("1/5 Ingesta de datos crudos -> DuckDB", [sys.executable, "-m", "src.ingest"])
    _run_step("2/5 dbt deps (instala dbt_utils)", [*DBT_CMD, "deps", *dbt_common_args])
    _run_step("3/5 dbt seed (dimensión de equipos CAEX)", [*DBT_CMD, "seed", *dbt_common_args])
    _run_step("4/5 dbt run (staging -> intermediate -> marts -> ml)", [*DBT_CMD, "run", *dbt_common_args])
    _run_step("5/5 dbt test (genéricos + dbt_utils + custom)", [*DBT_CMD, "test", *dbt_common_args])

    print(f"\nPipeline completo (target={args.target}).")
    if args.target == "dev":
        print("Base de datos lista en data/mining_dw.duckdb")


if __name__ == "__main__":
    main()
