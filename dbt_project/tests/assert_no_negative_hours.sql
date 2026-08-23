-- Falla si hay horas operativas negativas en el desempeño de equipos --
-- restricción de integridad física básica.
select camion_id, fecha, turno, horas_operativas
from {{ ref('int_equipment_performance') }}
where horas_operativas < 0
