-- Tabla 2.3: totales publicados (Codelco, otros productores y nacional), en miles de toneladas.
select
    anio,
    max(case when etiqueta = 'CODELCO' then valor end) as codelco_kt,
    max(case when etiqueta = 'OTROS PRODUCTORES' then valor end) as privados_kt,
    max(case when etiqueta = 'TOTAL PRODUCCIÓN' then valor end) as total_kt
from {{ ref('stg_cochilco__anuario') }}
where tabla = '2.3' and nivel = 0
group by anio
