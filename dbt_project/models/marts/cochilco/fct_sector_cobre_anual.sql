-- Grano: una fila por año. Indicadores del sector cobre chileno desde el anuario de Cochilco: producción,
-- ley del mineral, energía, agua, precio y los índices agregados de costo y productividad (GMP-10 + Codelco).
with energia as (
    select
        anio,
        sum(case when proceso = 'Total' then energia_tj end) as energia_total_tj,
        sum(case when proceso = 'Total' and fuente = 'electricidad' then energia_tj end) as electricidad_total_tj,
        sum(case when proceso = 'Concentradora' and fuente = 'electricidad' then energia_tj end)
            as electricidad_concentradora_tj
    from {{ ref('stg_cochilco__energia_proceso') }}
    group by anio
),
intensidad as (
    select
        anio,
        max(case when proceso = 'Concentradora' then mj_por_t_procesada end) as concentradora_mj_t_procesada,
        max(case when proceso = 'Concentradora' then mj_por_t_fino end) as concentradora_mj_t_fino
    from {{ ref('stg_cochilco__intensidad_energia') }}
    group by anio
),
agua as (
    select
        anio,
        max(case when proceso = 'Concentración' then nacional_m3_t end) as agua_concentracion_m3_t,
        max(case when proceso = 'Hidrometalurgia' then nacional_m3_t end) as agua_hidrometalurgia_m3_t
    from {{ ref('stg_cochilco__agua') }}
    group by anio
),
indices as (
    select anio, indice_costo, indice_productividad
    from {{ ref('stg_cochilco__indices_faena') }}
    where entidad = 'GMP-10 + Codelco'
),
precio as (
    select anio, promedio_usc_lb as precio_lme_usc_lb
    from {{ ref('stg_cochilco__precios') }}
    where metal = 'Cobre' and bolsa = 'LME'
)
select
    t.anio,
    t.total_kt as produccion_total_kt,
    t.codelco_kt as produccion_codelco_kt,
    round(100 * t.codelco_kt / t.total_kt, 2) as participacion_codelco_pct,
    l.ley_concentradora_pct,
    l.ley_lixiviacion_pilas_pct,
    l.ley_promedio_pct,
    e.energia_total_tj,
    e.electricidad_total_tj,
    e.electricidad_concentradora_tj,
    i.concentradora_mj_t_procesada,
    round(i.concentradora_mj_t_procesada / 3.6, 2) as concentradora_kwh_t_procesada,
    i.concentradora_mj_t_fino,
    a.agua_concentracion_m3_t,
    a.agua_hidrometalurgia_m3_t,
    x.indice_costo,
    x.indice_productividad,
    p.precio_lme_usc_lb
from {{ ref('stg_cochilco__produccion_total') }} t
left join {{ ref('stg_cochilco__ley_mineral') }} l on l.anio = t.anio
left join energia e on e.anio = t.anio
left join intensidad i on i.anio = t.anio
left join agua a on a.anio = t.anio
left join indices x on x.anio = t.anio
left join precio p on p.anio = t.anio
