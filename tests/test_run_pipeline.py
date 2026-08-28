import duckdb
import pytest

from run_pipeline import validate_duckdb_schema


def _make_db(tmp_path, tables: dict[str, list[str]]):
    db_path = tmp_path / "schema_test.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        for table, columns in tables.items():
            cols_sql = ", ".join(f"{c} integer" for c in columns)
            con.execute(f"create table {table} ({cols_sql})")
    finally:
        con.close()
    return db_path


def test_validate_duckdb_schema_passes_when_contract_is_satisfied(tmp_path):
    db_path = _make_db(tmp_path, {"fct_daily_mining_kpis": ["fecha", "turno", "faena"]})
    contract = {"fct_daily_mining_kpis": ["fecha", "turno", "faena"]}
    validate_duckdb_schema(db_path=db_path, contract=contract)  # no debe lanzar


def test_validate_duckdb_schema_fails_on_missing_table(tmp_path):
    db_path = _make_db(tmp_path, {"fct_daily_mining_kpis": ["fecha"]})
    contract = {"fct_daily_mining_kpis": ["fecha"], "ml_predictive_maintenance": ["camion_id"]}

    with pytest.raises(RuntimeError, match="ml_predictive_maintenance"):
        validate_duckdb_schema(db_path=db_path, contract=contract)


def test_validate_duckdb_schema_fails_on_missing_column(tmp_path):
    db_path = _make_db(tmp_path, {"fct_daily_mining_kpis": ["fecha", "turno"]})
    contract = {"fct_daily_mining_kpis": ["fecha", "turno", "faena"]}

    with pytest.raises(RuntimeError, match="faena"):
        validate_duckdb_schema(db_path=db_path, contract=contract)


def test_validate_duckdb_schema_fails_when_db_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_duckdb_schema(db_path=tmp_path / "no_existe.duckdb", contract={"x": ["y"]})
