with source as (
    select * from {{ source('raw', 'raw_flotation_telemetry') }}
)

select
    record_id,
    faena,
    ts,
    cast(ts as date) as fecha,
    turno,
    tonelaje_hora_ton,
    ley_alimentacion_cu_pct,
    ley_concentrado_cu_pct,
    ley_cola_cu_pct,
    dosis_reactivo_gpt,
    ph_pulpa
from source
where tonelaje_hora_ton is not null
