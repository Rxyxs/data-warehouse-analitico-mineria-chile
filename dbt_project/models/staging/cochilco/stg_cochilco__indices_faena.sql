-- Tablas 2.5 (costo unitario total, base real 2005 = 100) y 2.6 (productividad laboral, base 2005 = 100).
select
    anio,
    etiqueta as entidad,
    max(case when tabla = '2.5' then valor end) as indice_costo,
    max(case when tabla = '2.6' then valor end) as indice_productividad
from {{ ref('stg_cochilco__anuario') }}
where tabla in ('2.5', '2.6')
group by anio, etiqueta
