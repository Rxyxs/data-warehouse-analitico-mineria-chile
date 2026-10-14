-- Tabla 2.4: ley media de cobre del mineral procesado (%), por proceso.
select
    anio,
    max(case when etiqueta = 'Concentradora' then valor end) as ley_concentradora_pct,
    max(case when etiqueta = 'Lixiviación en pilas' then valor end) as ley_lixiviacion_pilas_pct,
    max(case when etiqueta = 'Lixiviación ROM y/o dump' then valor end) as ley_lixiviacion_rom_pct,
    max(case when etiqueta = 'Promedio Chile' then valor end) as ley_promedio_pct
from {{ ref('stg_cochilco__anuario') }}
where tabla = '2.4'
group by anio
