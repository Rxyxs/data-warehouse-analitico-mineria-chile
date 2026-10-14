-- Tabla 6.5: consumo de energía (TJ) por proceso y fuente. Se descartan los subtotales para no contar dos
-- veces; el consumo nacional queda aparte como proceso 'Total'.
select
    anio,
    case when padre = 'CONSUMO TOTAL DE ENERGÍA' then 'Total' else padre end as proceso,
    lower(etiqueta) as fuente,
    valor as energia_tj
from {{ ref('stg_cochilco__anuario') }}
where tabla = '6.5' and etiqueta in ('Combustibles', 'Electricidad') and valor is not null
