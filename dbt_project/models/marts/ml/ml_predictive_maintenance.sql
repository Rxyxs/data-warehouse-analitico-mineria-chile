{{ config(materialized='view') }}

-- Vista analítica lista para consumo directo por un modelo de mantenimiento
-- preventivo (RUL / clasificación de falla), grano (camion_id, fecha, turno) --
-- el mismo grano que int_equipment_performance, mas features de ingeniería
-- temporal (rolling windows, lags) que un mart de reporting no necesita pero
-- un modelo predictivo si. Ver chile-mining-predictive-maintenance para el
-- consumidor real de esta forma de feature view.

with base as (
    select
        *,
        -- Clave de orden cronologico por camion: fecha + turno (Dia antes que
        -- Noche dentro del mismo dia) -- necesaria porque las funciones de
        -- ventana no pueden ordenar directamente por una columna de texto
        -- ('Día'/'Noche') y obtener el orden temporal correcto.
        case turno when 'Día' then 0 else 1 end as turno_orden,
        case when horas_falla_no_programada > 0 then 1 else 0 end as falla_no_programada_flag
    from {{ ref('int_equipment_performance') }}
),

con_grupo_falla as (
    -- Un motor SQL no permite anidar una funcion de ventana dentro del
    -- PARTITION BY de otra en el mismo nivel de SELECT, asi que la suma
    -- acumulada que define cada "racha entre fallas" se calcula en su propia
    -- CTE antes de usarla como clave de particion del row_number() siguiente.
    select
        *,
        sum(falla_no_programada_flag) over (
            partition by camion_id order by fecha, turno_orden
            rows between unbounded preceding and current row
        ) as grupo_falla
    from base
),

con_ventanas as (
    select
        *,
        -- Racha de turnos consecutivos (por camion) desde el ultimo turno con
        -- una falla no programada -- proxy de "tiempo desde el ultimo evento",
        -- la feature central de cualquier formulacion de RUL.
        row_number() over (
            partition by camion_id, grupo_falla
            order by fecha, turno_orden
        ) - 1 as turnos_desde_ultima_falla,

        -- Ventanas moviles rezagadas (7 turnos ~ 3.5 dias, 2 turnos/dia) sobre
        -- disponibilidad y horas de falla -- todas "trailing" (rows between 6
        -- preceding and current row), sin fuga de informacion futura.
        avg(disponibilidad_pct) over (
            partition by camion_id order by fecha, turno_orden
            rows between 6 preceding and current row
        ) as disponibilidad_rolling_7t,
        sum(horas_falla_no_programada) over (
            partition by camion_id order by fecha, turno_orden
            rows between 6 preceding and current row
        ) as horas_falla_rolling_7t,
        sum(horas_mantencion_programada) over (
            partition by camion_id order by fecha, turno_orden
            rows between 6 preceding and current row
        ) as horas_mantencion_rolling_7t,

        -- Horas operativas acumuladas del camion a la fecha -- proxy de
        -- desgaste/antigüedad de uso, analogo a operating_hours en el modelo
        -- de RUL de chile-mining-predictive-maintenance.
        sum(horas_operativas) over (
            partition by camion_id order by fecha, turno_orden
            rows between unbounded preceding and current row
        ) as horas_operativas_acumuladas,

        -- Target de siguiente turno (lead, no lag): lo que un modelo de
        -- clasificacion de falla intentaria predecir a partir de las features
        -- del turno actual. Queda null en el ultimo turno observado de cada
        -- camion (no hay "siguiente" turno todavia).
        lead(falla_no_programada_flag) over (
            partition by camion_id order by fecha, turno_orden
        ) as falla_siguiente_turno
    from con_grupo_falla
)

select
    fecha,
    turno,
    faena,
    camion_id,
    modelo,
    capacidad_nominal_ton,
    horas_operativas,
    horas_operativas_acumuladas,
    horas_mantencion_programada,
    horas_mantencion_rolling_7t,
    horas_falla_no_programada,
    horas_falla_rolling_7t,
    disponibilidad_pct,
    disponibilidad_rolling_7t,
    desempeno_pct,
    turnos_desde_ultima_falla,
    falla_no_programada_flag,
    falla_siguiente_turno
from con_ventanas
order by camion_id, fecha, turno_orden
