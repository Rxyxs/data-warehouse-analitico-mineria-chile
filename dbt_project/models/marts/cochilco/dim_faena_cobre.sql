-- Faenas de cobre del anuario con su propiedad y su primer y último año con producción.
select
    faena,
    propiedad,
    min(anio) as primer_anio,
    max(anio) as ultimo_anio,
    sum(produccion_kt) as produccion_acumulada_kt
from {{ ref('stg_cochilco__produccion_faena') }}
where faena <> 'Otros'
group by faena, propiedad
