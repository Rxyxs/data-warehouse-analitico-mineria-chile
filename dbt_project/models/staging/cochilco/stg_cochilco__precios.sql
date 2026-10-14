-- Tabla 8.21: precios anuales de metales (centavos de dólar por libra). Cobre por bolsa; otros metales en LME.
select
    anio,
    case when grupo = 'COBRE REFINADO' then 'Cobre' else padre end as metal,
    case
        when grupo <> 'COBRE REFINADO' then 'LME'
        when padre = 'Bolsa de Metales de Londres' then 'LME'
        when padre = 'Bolsa de Metales de Shanghai' then 'SHFE'
        else padre
    end as bolsa,
    max(case when etiqueta = 'Promedio anual' then valor end) as promedio_usc_lb,
    max(case when etiqueta = 'Mínimo anual' then valor end) as minimo_usc_lb,
    max(case when etiqueta = 'Máximo anual' then valor end) as maximo_usc_lb
from {{ ref('stg_cochilco__anuario') }}
where tabla = '8.21'
group by 1, 2, 3
