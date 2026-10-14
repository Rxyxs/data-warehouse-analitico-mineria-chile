-- Grano: una fila por (anio, faena). Producción real con participación nacional, variación anual y, cuando
-- Cochilco los publica para esa faena, los índices de costo unitario y productividad laboral (base 2005 = 100).
with prod as (
    select * from {{ ref('stg_cochilco__produccion_faena') }}
),
tot as (
    select anio, total_kt from {{ ref('stg_cochilco__produccion_total') }}
)
select
    p.anio,
    p.faena,
    p.propiedad,
    p.produccion_kt,
    round(100 * p.produccion_kt / t.total_kt, 3) as participacion_pct,
    p.produccion_kt - lag(p.produccion_kt) over (partition by p.faena order by p.anio) as variacion_kt,
    i.indice_costo,
    i.indice_productividad
from prod p
join tot t on t.anio = p.anio
left join {{ ref('stg_cochilco__indices_faena') }} i
    on i.anio = p.anio and i.entidad = p.faena
