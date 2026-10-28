-- Costo marginal real por día y barra (USD/MWh). Se dejan las seis barras con serie completa 2022-2025;
-- Tarapacá y Atacama solo aparecen en los informes desde julio de 2025.
select
    cast(fecha as date) as fecha,
    year(fecha) as anio,
    month(fecha) as mes,
    barra,
    case when barra in ('Crucero', 'Cardones', 'Pan de Azucar') then 'Norte' else 'Centro-sur' end as zona,
    cmg_promedio_usd_mwh,
    cmg_horas_solares_usd_mwh,
    cmg_noche_usd_mwh,
    horas
from {{ source('raw', 'raw_cen_cmg_diario') }}
where barra in ('Crucero', 'Cardones', 'Pan de Azucar', 'Quillota', 'Charrua', 'Puerto Montt')
