{{ config(materialized='view') }}

-- Vista analítica lista para consumo directo por un modelo de predicción de
-- ley de mineral / recuperación metalúrgica, grano horario (faena, ts) --
-- mas fino que fct_daily_mining_kpis (turno) a propósito, porque un modelo
-- de proceso metalúrgico necesita ver la dinámica hora a hora de reactivo/pH
-- para predecir la ley de concentrado, no solo un promedio de turno.

with base as (
    select * from {{ ref('stg_flotation') }}
),

con_ventanas as (
    select
        *,
        -- Recuperación metalúrgica de ESTA hora puntual (no agregada) -- el
        -- mismo macro que usa fct_daily_mining_kpis a nivel de turno, aplicado
        -- fila a fila para que sirva como target o feature de un modelo.
        {{ metallurgical_recovery('ley_alimentacion_cu_pct', 'ley_concentrado_cu_pct', 'ley_cola_cu_pct') }}
            as recuperacion_cu_pct,

        -- Autoregresivo: la ley de concentrado de la hora anterior es
        -- tipicamente el predictor individual mas fuerte de la hora actual
        -- en un proceso de flotacion con inercia (no cambia instantaneamente).
        lag(ley_concentrado_cu_pct) over (
            partition by faena order by ts
        ) as ley_concentrado_lag_1h,
        lag(ley_alimentacion_cu_pct) over (
            partition by faena order by ts
        ) as ley_alimentacion_lag_1h,

        -- Ventanas moviles rezagadas de 6 horas sobre las variables de
        -- control de proceso -- capturan tendencia reciente de dosificacion
        -- y pH sin usar informacion futura.
        avg(dosis_reactivo_gpt) over (
            partition by faena order by ts
            rows between 5 preceding and current row
        ) as dosis_reactivo_rolling_6h,
        avg(ph_pulpa) over (
            partition by faena order by ts
            rows between 5 preceding and current row
        ) as ph_pulpa_rolling_6h,
        avg(tonelaje_hora_ton) over (
            partition by faena order by ts
            rows between 5 preceding and current row
        ) as tonelaje_rolling_6h,
        stddev_samp(ley_alimentacion_cu_pct) over (
            partition by faena order by ts
            rows between 5 preceding and current row
        ) as ley_alimentacion_volatilidad_6h
    from base
)

select
    record_id,
    faena,
    ts,
    fecha,
    turno,
    tonelaje_hora_ton,
    tonelaje_rolling_6h,
    ley_alimentacion_cu_pct,
    ley_alimentacion_lag_1h,
    ley_alimentacion_volatilidad_6h,
    dosis_reactivo_gpt,
    dosis_reactivo_rolling_6h,
    ph_pulpa,
    ph_pulpa_rolling_6h,
    ley_concentrado_lag_1h,
    ley_cola_cu_pct,
    -- Targets: la ley de concentrado real de esta hora, y la recuperacion
    -- metalurgica resultante -- ambos disponibles solo retrospectivamente,
    -- exactamente lo que un modelo entrenado sobre este historico intentaria
    -- predecir a partir de las columnas de arriba.
    ley_concentrado_cu_pct as target_ley_concentrado_cu_pct,
    recuperacion_cu_pct as target_recuperacion_cu_pct
from con_ventanas
order by faena, ts
