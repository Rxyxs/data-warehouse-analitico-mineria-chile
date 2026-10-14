"""Ingesta real del anuario de Cochilco: parser de hojas anchas y tabla larga versionada."""
import pandas as pd
import pytest

from src import ingest_cochilco as IC

SHEET = [
    ("Tabla 2.3", None, None, None),
    ("Producción / Production", None, None, None),
    (None, 2023, 2024, 2025),
    ("CODELCO", 1424.5, 1328.0, 1307.2),
    ("     División El Teniente (2) / El Teniente Division", 359.6, 357.0, "n.d."),
    ("     División Andina", 160.0, 161.0, 170.0),
    ("OTROS PRODUCTORES / Other producers", 3825.9, 4177.9, 4081.0),
    ("\xa0\xa0Escondida", 1102.1, 1279.1, 1345.1),
    ("TOTAL PRODUCCIÓN", 5250.4, 5505.9, 5388.2),
    ("(1) Nota al pie", None, None, None),
    ("Fuente / Source: Cochilco", None, None, None),
]


@pytest.fixture(scope="module")
def parsed():
    return IC.parse_table(SHEET, "2.3")


def test_label_drops_translation_and_footnote_marks():
    assert IC.clean_label("     División El Teniente (2) / El Teniente Division") == "División El Teniente"


def test_hard_spaces_count_as_indentation(parsed):
    esc = parsed[parsed["etiqueta"] == "Escondida"].iloc[0]
    assert esc["nivel"] == 1 and esc["padre"] == "OTROS PRODUCTORES"


def test_hierarchy_and_long_shape(parsed):
    assert set(parsed["anio"]) == {2023, 2024, 2025}
    tenie = parsed[parsed["etiqueta"] == "División El Teniente"]
    assert (tenie["grupo"] == "CODELCO").all() and (tenie["nivel"] == 1).all()
    assert parsed[parsed["etiqueta"] == "TOTAL PRODUCCIÓN"]["nivel"].eq(0).all()


def test_missing_markers_become_null_and_footnotes_end_the_table(parsed):
    v = parsed.query("etiqueta == 'División El Teniente' and anio == 2025").iloc[0]
    assert pd.isna(v["valor"]) and v["valor_original"] == "n.d."
    assert not parsed["etiqueta"].str.startswith(("(1)", "Fuente")).any()


def test_sheet_without_year_header_is_rejected():
    with pytest.raises(ValueError):
        IC.parse_table([("Sin años", 1, 2)], "9.9")


def test_versioned_long_table_reconciles_with_published_totals():
    d = pd.read_csv(IC.LONG_CSV, dtype={"tabla": str})
    assert set(d["tabla"]) == set(IC.TABLES)
    p = d[d["tabla"] == "2.3"]
    mines = p[p["nivel"] == 1].groupby("anio")["valor"].sum()
    total = p[p["etiqueta"] == "TOTAL PRODUCCIÓN"].set_index("anio")["valor"]
    assert (mines - total).abs().max() < 0.5
    assert total.between(4000, 7000).all()
