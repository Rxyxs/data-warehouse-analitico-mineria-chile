import random

import duckdb

from src.ingest import (
    build_database,
    generate_caex_maintenance,
    generate_flotation_telemetry,
    generate_safety_incidents,
)


def test_flotation_grades_are_physically_consistent():
    df = generate_flotation_telemetry(random.Random(1))
    assert (df["ley_alimentacion_cu_pct"] > df["ley_cola_cu_pct"]).all()
    assert (df["ley_concentrado_cu_pct"] > df["ley_alimentacion_cu_pct"]).all()
    assert (df["tonelaje_hora_ton"] > 0).all()


def test_maintenance_hours_never_exceed_shift_length():
    df = generate_caex_maintenance(random.Random(2))
    assert (df["horas_operativas"] >= 0).all()
    horas_usadas = (
        df["horas_operativas"] + df["horas_mantencion_programada"] + df["horas_falla_no_programada"]
    )
    assert (horas_usadas <= df["horas_turno_programadas"] + 1e-6).all()


def test_safety_incident_severity_values_are_valid():
    df = generate_safety_incidents(random.Random(3))
    assert set(df["severidad"].unique()) <= {"LEVE", "GRAVE", "FATAL"}
    assert (df["horas_detencion_asociadas"] >= 0).all()


def test_build_database_creates_expected_tables(tmp_path):
    db_path = tmp_path / "test_mining_dw.duckdb"
    counts = build_database(db_path)

    assert db_path.exists()
    assert set(counts.keys()) == {
        "raw_flotation_telemetry",
        "raw_caex_maintenance",
        "raw_safety_incidents",
    }
    assert all(n > 0 for n in counts.values())

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        for table, expected_n in counts.items():
            actual_n = con.execute(f"select count(*) from {table}").fetchone()[0]
            assert actual_n == expected_n
    finally:
        con.close()
