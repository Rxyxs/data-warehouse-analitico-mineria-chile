-- La energía por proceso (sin subtotales) debe sumar el consumo nacional publicado, por fuente (tolerancia 1%).
with procesos as (
    select anio, fuente, sum(energia_tj) as suma
    from {{ ref('stg_cochilco__energia_proceso') }}
    where proceso <> 'Total'
    group by anio, fuente
)
select p.anio, p.fuente, p.suma, t.energia_tj
from procesos p
join {{ ref('stg_cochilco__energia_proceso') }} t
    on t.anio = p.anio and t.fuente = p.fuente and t.proceso = 'Total'
where abs(p.suma - t.energia_tj) > 0.01 * t.energia_tj
