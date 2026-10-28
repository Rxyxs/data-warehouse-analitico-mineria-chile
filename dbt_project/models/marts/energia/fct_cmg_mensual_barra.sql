-- Grano: una fila por (mes, barra). Costo marginal real promedio del mes, en horas solares y de noche, y la
-- brecha noche - horas solares: cuánto más caro es consumir de noche que a mediodía en cada barra.
select
    make_date(anio, mes, 1) as mes,
    barra,
    any_value(zona) as zona,
    count(*) as dias,
    round(avg(cmg_promedio_usd_mwh), 2) as cmg_promedio_usd_mwh,
    round(avg(cmg_horas_solares_usd_mwh), 2) as cmg_horas_solares_usd_mwh,
    round(avg(cmg_noche_usd_mwh), 2) as cmg_noche_usd_mwh,
    round(avg(cmg_noche_usd_mwh) - avg(cmg_horas_solares_usd_mwh), 2) as brecha_noche_solar_usd_mwh
from {{ ref('stg_cen__cmg_diario') }}
group by anio, mes, barra
