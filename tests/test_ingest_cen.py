"""Ingesta real del costo marginal del SEN: resumen diario por barra."""
import pandas as pd
import pytest

from src import ingest_cen as IC


def _hourly(values):
    """Un día de una barra; la hora h del informe es el bloque que empieza a las h-1."""
    return pd.DataFrame({"date": "2024-01-01", "hour": range(1, 25), "bar": "Crucero", "cmg_usd_mwh": values})


def test_daily_summary_splits_solar_hours_and_night():
    # 100 USD/MWh de noche, 0 entre las 10:00 y las 16:59, 50 en el resto.
    values = [100.0 if (h - 1) in IC.NIGHT_HOURS else 0.0 if (h - 1) in IC.SOLAR_HOURS else 50.0 for h in range(1, 25)]
    d = IC.daily_summary(_hourly(values)).iloc[0]
    assert d["cmg_noche_usd_mwh"] == 100.0
    assert d["cmg_horas_solares_usd_mwh"] == 0.0
    assert d["cmg_promedio_usd_mwh"] == pytest.approx(sum(values) / 24, abs=0.01)
    assert d["horas"] == 24


def test_daily_summary_clips_reconstruction_noise_below_zero():
    d = IC.daily_summary(_hourly([-0.15] * 24)).iloc[0]
    assert d["cmg_promedio_usd_mwh"] == 0.0


def test_versioned_table_covers_2022_2025_for_the_six_buses():
    df = pd.read_csv(IC.DAILY_CSV)
    six = df[df["barra"].isin(["Crucero", "Cardones", "Pan de Azucar", "Quillota", "Charrua", "Puerto Montt"])]
    assert six["fecha"].min().startswith("2022") and six["fecha"].max().startswith("2025-12")
    assert six.groupby("barra").size().min() > 1300
    assert (df["cmg_promedio_usd_mwh"] >= 0).all()
