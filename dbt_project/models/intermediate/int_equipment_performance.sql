with maintenance as (
    select * from {{ ref('stg_maintenance') }}
),

equipo as (
    select * from {{ ref('dim_equipos_caex') }}
),

joined as (
    select
        m.fecha,
        m.turno,
        m.faena,
        m.camion_id,
        e.modelo,
        e.capacidad_nominal_ton,
        e.ciclos_hora_nominal,
        m.horas_turno_programadas,
        m.horas_operativas,
        m.horas_mantencion_programada,
        m.horas_falla_no_programada,
        m.num_ciclos,
        (m.num_ciclos * e.capacidad_nominal_ton * m.fill_factor) as tonelaje_transportado_ton
    from maintenance m
    left join equipo e on m.camion_id = e.camion_id
),

calculado as (
    select
        *,
        {{ safe_divide('horas_operativas', 'horas_turno_programadas') }} as disponibilidad_pct,
        {{ safe_divide('tonelaje_transportado_ton', 'horas_operativas') }} as tasa_ton_hora_real,
        (capacidad_nominal_ton * ciclos_hora_nominal) as tasa_ton_hora_nominal
    from joined
)

select
    fecha,
    turno,
    faena,
    camion_id,
    modelo,
    capacidad_nominal_ton,
    horas_turno_programadas,
    horas_operativas,
    horas_mantencion_programada,
    horas_falla_no_programada,
    num_ciclos,
    tonelaje_transportado_ton,
    disponibilidad_pct,
    tasa_ton_hora_real,
    tasa_ton_hora_nominal,
    -- Se acota a 1.0 (100%): por convencion de OEE, un desempeno "real" que supera
    -- el nominal se interpreta como una referencia de capacidad desactualizada, no
    -- como sobre-cumplimiento genuino -- evita que oee_pct aguas abajo supere 100%.
    least({{ safe_divide('tasa_ton_hora_real', 'tasa_ton_hora_nominal') }}, 1.0) as desempeno_pct
from calculado
