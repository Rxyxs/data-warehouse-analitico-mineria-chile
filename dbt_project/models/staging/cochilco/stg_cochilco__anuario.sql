-- Anuario de Cochilco en formato largo, tipado. Fuente real (src/ingest_cochilco.py).
-- En los índices de costo y productividad (tablas 2.5 y 2.6) un 0 significa "sin dato", no un índice nulo.
select
    cast(tabla as varchar) as tabla,
    cast(orden as integer) as orden,
    cast(nivel as integer) as nivel,
    etiqueta,
    padre,
    grupo,
    cast(anio as integer) as anio,
    case when cast(tabla as varchar) in ('2.5', '2.6') and valor = 0 then null else cast(valor as double) end as valor,
    unidad
from {{ source('raw', 'raw_cochilco_anuario') }}
