-- Falla si existe más de una fila por combinación (fecha, turno, faena) en el
-- mart final -- el grano declarado del hecho debe ser único.
select fecha, turno, faena, count(*) as n_filas
from {{ ref('fct_daily_mining_kpis') }}
group by 1, 2, 3
having count(*) > 1
