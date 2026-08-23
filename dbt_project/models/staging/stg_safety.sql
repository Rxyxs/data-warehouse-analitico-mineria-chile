with source as (
    select * from {{ source('raw', 'raw_safety_incidents') }}
)

select
    incident_id,
    faena,
    fecha,
    turno,
    camion_id,
    upper(severidad) as severidad,
    tipo_incidente,
    coalesce(horas_detencion_asociadas, 0) as horas_detencion_asociadas
from source
