-- Tabla 2.3: producción de cobre fino por faena (miles de toneladas). Solo faenas (nivel 1); los totales
-- de grupo y nacional quedan en stg_cochilco__produccion_total para el test de conciliación.
select
    anio,
    etiqueta as faena,
    case when grupo = 'CODELCO' then 'Codelco' else 'Privada' end as propiedad,
    valor as produccion_kt
from {{ ref('stg_cochilco__anuario') }}
where tabla = '2.3' and nivel = 1 and valor is not null
