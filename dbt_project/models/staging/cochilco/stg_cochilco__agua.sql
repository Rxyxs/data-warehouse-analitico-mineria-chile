-- Tabla 6.3: consumo unitario de agua (m3 por tonelada de mineral). Las filas "TOTAL NACIONAL" no tienen
-- sangría en el Excel, así que heredan el proceso de la sección anterior según el orden de la hoja.
with filas as (
    select
        anio, orden, etiqueta, valor,
        last_value(case when etiqueta <> 'TOTAL NACIONAL' then grupo end ignore nulls)
            over (partition by anio order by orden rows between unbounded preceding and current row) as seccion
    from {{ ref('stg_cochilco__anuario') }}
    where tabla = '6.3'
)
select
    anio,
    case when seccion like 'CONCENTRACI%' then 'Concentración' else 'Hidrometalurgia' end as proceso,
    max(case when etiqueta = 'Gran Minería del Cobre' then valor end) as gran_mineria_m3_t,
    max(case when etiqueta = 'Mediana Minería del Cobre' then valor end) as mediana_mineria_m3_t,
    max(case when etiqueta = 'TOTAL NACIONAL' then valor end) as nacional_m3_t
from filas
where seccion not like 'CONSUMO UNITARIO%'
group by 1, 2
