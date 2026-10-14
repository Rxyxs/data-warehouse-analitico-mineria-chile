-- Tablas 6.8 (MJ por tonelada de cobre fino) y 6.9 (MJ por tonelada de material procesado), por proceso.
select
    anio,
    case etiqueta when 'Mina Rajo' then 'Mina rajo' when 'Mina Subterránea' then 'Mina subterránea'
                  when 'LX-SX-EW' then 'Lixiviación (SX-EW)' else etiqueta end as proceso,
    max(case when tabla = '6.8' then valor end) as mj_por_t_fino,
    max(case when tabla = '6.9' then valor end) as mj_por_t_procesada
from {{ ref('stg_cochilco__anuario') }}
where tabla in ('6.8', '6.9')
group by 1, 2
