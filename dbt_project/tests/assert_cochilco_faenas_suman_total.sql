-- Conciliación del anuario: las faenas suman su grupo (Codelco / otros) y los grupos suman el total nacional.
with faenas as (
    select anio, propiedad, sum(produccion_kt) as suma
    from {{ ref('stg_cochilco__produccion_faena') }}
    group by anio, propiedad
),
grupos as (
    select anio, 'Codelco' as propiedad, codelco_kt as publicado from {{ ref('stg_cochilco__produccion_total') }}
    union all
    select anio, 'Privada', privados_kt from {{ ref('stg_cochilco__produccion_total') }}
)
select f.anio, f.propiedad, f.suma, g.publicado
from faenas f
join grupos g on g.anio = f.anio and g.propiedad = f.propiedad
where abs(f.suma - g.publicado) > 0.5
union all
select anio, 'Total', codelco_kt + privados_kt, total_kt
from {{ ref('stg_cochilco__produccion_total') }}
where abs(codelco_kt + privados_kt - total_kt) > 0.5
