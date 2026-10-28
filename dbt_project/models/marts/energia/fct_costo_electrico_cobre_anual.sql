-- Grano: una fila por (anio, barra). La electricidad que consume la minería del cobre (Cochilco, tabla 6.5)
-- valorizada al costo marginal real promedio de cada barra: un costo de oportunidad a precio spot, no lo que
-- pagan las faenas (compran casi toda su energía por contratos). Solo años con al menos 330 días de precio.
with precio as (
    select anio, barra, count(*) as dias_con_precio, avg(cmg_promedio_usd_mwh) as cmg_promedio_usd_mwh
    from {{ ref('stg_cen__cmg_diario') }}
    group by anio, barra
    having count(*) >= 330
),
electricidad as (
    select
        anio,
        sum(case when proceso = 'Total' then energia_tj end) as electricidad_total_tj,
        sum(case when proceso = 'Concentradora' then energia_tj end) as electricidad_concentradora_tj
    from {{ ref('stg_cochilco__energia_proceso') }}
    where fuente = 'electricidad'
    group by anio
),
cobre as (
    select anio, total_kt from {{ ref('stg_cochilco__produccion_total') }}
)
select
    p.anio,
    p.barra,
    p.dias_con_precio,
    round(p.cmg_promedio_usd_mwh, 2) as cmg_promedio_usd_mwh,
    round(e.electricidad_total_tj * 1e6 / 3600, 0) as electricidad_total_mwh,
    round(e.electricidad_total_tj * 1e6 / 3600 * p.cmg_promedio_usd_mwh / 1e6, 1) as costo_spot_electricidad_musd,
    round(e.electricidad_concentradora_tj * 1e6 / 3600 * p.cmg_promedio_usd_mwh / 1e6, 1) as costo_spot_concentradora_musd,
    round(e.electricidad_total_tj * 1e6 / 3600 * p.cmg_promedio_usd_mwh / (c.total_kt * 1000), 1)
        as costo_spot_usd_por_t_cobre
from precio p
join electricidad e using (anio)
join cobre c using (anio)
