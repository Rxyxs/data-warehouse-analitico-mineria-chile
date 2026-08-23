with source as (
    select * from {{ source('raw', 'raw_caex_maintenance') }}
)

select
    record_id,
    faena,
    camion_id,
    fecha,
    turno,
    horas_turno_programadas,
    horas_operativas,
    horas_mantencion_programada,
    horas_falla_no_programada,
    num_ciclos,
    fill_factor
from source
where horas_operativas is not null
