"""Dashboard ejecutivo Streamlit: KPIs unificados de minería (fct_daily_mining_kpis)
consultados directamente sobre DuckDB con SQL.

Ejecutar desde la raíz del repositorio con:
    streamlit run app.py

Requiere que data/mining_dw.duckdb ya exista (ejecutar antes `python -m src.orchestrator`).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "data" / "mining_dw.duckdb"

RISK_COLORS = {"Bajo": "#2ca02c", "Medio": "#ffcc00", "Alto": "#ff7f0e", "Crítico": "#d62728"}

st.set_page_config(page_title="Data Warehouse Minería Chile", layout="wide")


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=60)
def load_kpis() -> pd.DataFrame:
    con = get_connection()
    return con.execute("select * from fct_daily_mining_kpis order by fecha, faena, turno").df()


@st.cache_data(ttl=60)
def load_equipment() -> pd.DataFrame:
    con = get_connection()
    return con.execute(
        "select * from int_equipment_performance order by fecha, faena, camion_id"
    ).df()


def main() -> None:
    st.title("⛏️ Data Warehouse Analítico -- Minería Chile")
    st.caption(
        "KPIs unificados de flotación geometalúrgica, mantención CAEX y seguridad "
        "operacional, calculados con dbt sobre DuckDB (100% local)."
    )

    if not DB_PATH.exists():
        st.error(
            "No se encontró data/mining_dw.duckdb. Ejecuta primero: "
            "`python -m src.orchestrator`"
        )
        return

    kpis = load_kpis()
    if kpis.empty:
        st.warning("El mart fct_daily_mining_kpis está vacío.")
        return

    kpis["fecha"] = pd.to_datetime(kpis["fecha"])

    st.sidebar.header("Filtros")
    faenas_sel = st.sidebar.multiselect(
        "Faena", sorted(kpis["faena"].unique()), default=sorted(kpis["faena"].unique())
    )
    turnos_sel = st.sidebar.multiselect(
        "Turno", sorted(kpis["turno"].unique()), default=sorted(kpis["turno"].unique())
    )
    fecha_min, fecha_max = kpis["fecha"].min().date(), kpis["fecha"].max().date()
    rango_fechas = st.sidebar.date_input(
        "Rango de fechas", value=(fecha_min, fecha_max), min_value=fecha_min, max_value=fecha_max
    )

    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        fecha_desde, fecha_hasta = rango_fechas
    else:
        fecha_desde, fecha_hasta = fecha_min, fecha_max

    filtrado = kpis[
        kpis["faena"].isin(faenas_sel)
        & kpis["turno"].isin(turnos_sel)
        & (kpis["fecha"].dt.date >= fecha_desde)
        & (kpis["fecha"].dt.date <= fecha_hasta)
    ]

    if filtrado.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        return

    tab_resumen, tab_tendencias, tab_riesgo, tab_equipos = st.tabs(
        ["📊 Resumen ejecutivo", "📈 Tendencias", "⚠️ Riesgo operacional", "🚚 Desempeño de equipos"]
    )

    with tab_resumen:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("TIEE promedio", f"{filtrado['tiee_pct'].mean():.1f}%")
        col2.metric("OEE promedio", f"{filtrado['oee_pct'].mean():.1f}%")
        col3.metric("Recuperación Cu promedio", f"{filtrado['recuperacion_cu_pct'].mean():.1f}%")
        col4.metric("Incidentes totales", int(filtrado["total_incidentes"].sum()))

        st.subheader("Detalle por fecha / turno / faena")
        st.dataframe(
            filtrado[
                [
                    "fecha", "turno", "faena", "tiee_pct", "oee_pct", "calidad_pct",
                    "recuperacion_cu_pct", "total_incidentes", "nivel_riesgo",
                ]
            ],
            use_container_width=True,
            height=350,
        )

    with tab_tendencias:
        st.subheader("OEE y TIEE en el tiempo (promedio diario)")
        diario = filtrado.groupby("fecha")[["tiee_pct", "oee_pct", "desempeno_pct", "calidad_pct"]].mean()
        st.line_chart(diario)

        st.subheader("Recuperación metalúrgica de Cu en el tiempo")
        recuperacion_diaria = filtrado.groupby("fecha")["recuperacion_cu_pct"].mean()
        st.line_chart(recuperacion_diaria)

    with tab_riesgo:
        st.subheader("Distribución de turnos por nivel de riesgo")
        conteo_riesgo = filtrado["nivel_riesgo"].value_counts().reindex(
            ["Bajo", "Medio", "Alto", "Crítico"]
        ).fillna(0)
        st.bar_chart(conteo_riesgo)

        st.subheader("Turnos de riesgo Alto / Crítico")
        criticos = filtrado[filtrado["nivel_riesgo"].isin(["Alto", "Crítico"])].sort_values(
            "puntaje_riesgo_operacional", ascending=False
        )
        if criticos.empty:
            st.success("No hay turnos con nivel de riesgo Alto o Crítico en el rango seleccionado.")
        else:
            st.dataframe(
                criticos[
                    ["fecha", "turno", "faena", "total_incidentes", "incidentes_graves_fatales",
                     "puntaje_riesgo_operacional", "nivel_riesgo"]
                ],
                use_container_width=True,
            )

    with tab_equipos:
        st.subheader("Desempeño por camión CAEX")
        equipos = load_equipment()
        equipos["fecha"] = pd.to_datetime(equipos["fecha"])
        equipos_filtrado = equipos[
            equipos["faena"].isin(faenas_sel)
            & equipos["turno"].isin(turnos_sel)
            & (equipos["fecha"].dt.date >= fecha_desde)
            & (equipos["fecha"].dt.date <= fecha_hasta)
        ]
        resumen_camion = (
            equipos_filtrado.groupby(["camion_id", "faena", "modelo"])
            .agg(
                disponibilidad_pct=("disponibilidad_pct", "mean"),
                desempeno_pct=("desempeno_pct", "mean"),
                tonelaje_transportado_ton=("tonelaje_transportado_ton", "sum"),
            )
            .reset_index()
            .sort_values("tonelaje_transportado_ton", ascending=False)
        )
        resumen_camion["disponibilidad_pct"] = (resumen_camion["disponibilidad_pct"] * 100).round(1)
        resumen_camion["desempeno_pct"] = (resumen_camion["desempeno_pct"] * 100).round(1)
        st.dataframe(resumen_camion, use_container_width=True, height=350)


if __name__ == "__main__":
    main()
