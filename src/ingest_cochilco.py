"""Ingesta de datos reales: Anuario de Estadísticas del Cobre y Otros Minerales de Cochilco.

Cochilco publica la base de datos del anuario como un Excel con una hoja por tabla, todas con el
mismo formato ancho: una fila de encabezado con los años en columnas y filas con una etiqueta
bilingüe ("Escondida", "     División El Teniente", "Concentradora / Concentrator") cuya sangría
marca la jerarquía (Codelco -> divisiones; Concentradora -> Combustibles / Electricidad). Este
módulo convierte cada tabla seleccionada a formato largo (tabla, fila, año, valor) conservando esa
jerarquía, y la carga en DuckDB como ``raw_cochilco_anuario``.

La tabla larga se versiona en ``data/real/cochilco_anuario_long.csv`` para que el pipeline y los
tests corran sin red; ``--refresh`` la regenera desde el Excel oficial.

    python -m src.ingest_cochilco            # carga la tabla versionada en DuckDB
    python -m src.ingest_cochilco --refresh  # descarga el Excel y regenera la tabla
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "mining_dw.duckdb"
REAL_DIR = ROOT_DIR / "data" / "real"
LONG_CSV = REAL_DIR / "cochilco_anuario_long.csv"
RAW_XLSX = ROOT_DIR / "data" / "raw" / "cochilco_anuario_2000_2025.xlsx"
XLSX_URL = ("https://www.cochilco.cl/web/download/1036/2026/16850/"
            "base-de-datos-anuario-de-estadisticas-cochilco-2000-2025.xlsx")

# Tablas usadas por el warehouse y su unidad (la fila 5 de cada hoja la describe).
TABLES = {
    "2.3": "miles de TM de cobre fino",
    "2.4": "% de cobre en el mineral procesado",
    "2.5": "índice de costo unitario total, base real 2005 = 100",
    "2.6": "índice de productividad laboral, base 2005 = 100",
    "6.3": "m3 de agua por tonelada procesada",
    "6.5": "TJ",
    "6.8": "MJ por tonelada de cobre fino, según producto del proceso",
    "6.9": "MJ por tonelada de material extraído o procesado",
    "8.21": "centavos de dólar por libra",
}
MISSING = {"n.d.", "n.a.", "-", "", "s.i."}


def clean_label(raw: str) -> str:
    """'     División El Teniente (2) / El Teniente Division' -> 'División El Teniente'."""
    text = str(raw).split(" / ")[0]
    text = re.sub(r"\(\d+\)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def indent(raw: str) -> int:
    """Sangría de la etiqueta. Algunas hojas usan espacios normales y otras espacios duros (\xa0)."""
    text = str(raw)
    return len(text) - len(text.lstrip())


def parse_value(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in MISSING:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def parse_table(rows: list[tuple], table_id: str) -> pd.DataFrame:
    """Una hoja del anuario (lista de filas) en formato largo.

    El encabezado es la primera fila que tiene al menos tres años (enteros 1990-2100). Cada fila
    con etiqueta en la primera columna aporta un registro por año; la sangría define el nivel y el
    padre. Las notas al pie ("(1) ...", "Fuente / Source") cierran la tabla.
    """
    header_idx, year_cols = None, {}
    for i, row in enumerate(rows):
        cols = {j: int(c) for j, c in enumerate(row) if isinstance(c, (int, float)) and 1990 <= c <= 2100 and float(c).is_integer()}
        if len(cols) >= 3:
            header_idx, year_cols = i, cols
            break
    if header_idx is None:
        raise ValueError(f"Tabla {table_id}: no se encontró la fila de años")

    records, stack, order = [], [], 0
    for row in rows[header_idx + 1:]:
        label = row[0] if row else None
        if label is None or not str(label).strip():
            continue
        text = str(label).strip()
        if re.match(r"^\(\d+\)|^Fuente|^Elaborad|^n\.d\.|^n\.a\.|^Comisi", text):
            break
        level = indent(label)
        while stack and stack[-1][0] >= level:
            stack.pop()
        name = clean_label(label)
        parent = stack[-1][1] if stack else None
        group = stack[0][1] if stack else name
        stack.append((level, name))
        order += 1
        for j, year in year_cols.items():
            raw = row[j] if j < len(row) else None
            records.append({
                "tabla": table_id, "orden": order, "nivel": len(stack) - 1, "etiqueta": name,
                "padre": parent, "grupo": group, "anio": year, "valor": parse_value(raw),
                "valor_original": None if raw is None else str(raw),
            })
    return pd.DataFrame(records)


def parse_workbook(path: Path, tables: dict[str, str] = TABLES) -> pd.DataFrame:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    frames = []
    for table_id, unit in tables.items():
        rows = list(wb[f"Tabla {table_id}"].iter_rows(values_only=True))
        df = parse_table(rows, table_id)
        df["unidad"] = unit
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    # Filas de solo título (p. ej. "Concentradora" en la tabla 6.5) no tienen valores en ningún año.
    has_value = out.groupby(["tabla", "orden"])["valor"].transform(lambda s: s.notna().any())
    has_text = out.groupby(["tabla", "orden"])["valor_original"].transform(lambda s: s.notna().any())
    return out[has_value | has_text].reset_index(drop=True)


def refresh(xlsx: Path = RAW_XLSX) -> Path:
    import requests

    xlsx.parent.mkdir(parents=True, exist_ok=True)
    if not xlsx.exists():
        r = requests.get(XLSX_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
        r.raise_for_status()
        xlsx.write_bytes(r.content)
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    parse_workbook(xlsx).to_csv(LONG_CSV, index=False)
    return LONG_CSV


def load_into_duckdb(db_path: Path = DB_PATH, csv: Path = LONG_CSV) -> int:
    df = pd.read_csv(csv, dtype={"tabla": str, "valor_original": str})
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.register("cochilco_view", df)
        con.execute("CREATE OR REPLACE TABLE raw_cochilco_anuario AS SELECT * FROM cochilco_view")
        return int(con.execute("SELECT count(*) FROM raw_cochilco_anuario").fetchone()[0])
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="descargar el Excel oficial y regenerar la tabla larga")
    args = parser.parse_args()
    if args.refresh:
        refresh()
    n = load_into_duckdb()
    df = pd.read_csv(LONG_CSV, dtype={"tabla": str})
    print(f"raw_cochilco_anuario: {n} filas, {df['tabla'].nunique()} tablas, años {df['anio'].min()}-{df['anio'].max()}")


if __name__ == "__main__":
    main()
