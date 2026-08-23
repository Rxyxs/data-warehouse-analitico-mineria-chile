-- Falla si la recuperación metalúrgica calculada está fuera del rango físicamente
-- posible [0, 100]%.
select fecha, turno, faena, recuperacion_cu_pct
from {{ ref('fct_daily_mining_kpis') }}
where recuperacion_cu_pct is not null
  and (recuperacion_cu_pct < 0 or recuperacion_cu_pct > 100)
