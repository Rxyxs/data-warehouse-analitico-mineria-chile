with equipo_agg as (
    select
        fecha,
        turno,
        faena,
        count(distinct camion_id) as n_camiones_activos,
        avg(disponibilidad_pct) as disponibilidad_promedio,
        avg(desempeno_pct) as desempeno_promedio,
        sum(horas_turno_programadas) as horas_turno_totales,
        sum(horas_operativas) as horas_operativas_totales,
        sum(tonelaje_transportado_ton) as tonelaje_transportado_total
    from {{ ref('int_equipment_performance') }}
    group by 1, 2, 3
),

flotacion_agg as (
    select
        fecha,
        turno,
        faena,
        sum(tonelaje_hora_ton) as tonelaje_procesado_total,
        {{ safe_divide('sum(ley_alimentacion_cu_pct * tonelaje_hora_ton)', 'sum(tonelaje_hora_ton)') }} as ley_alimentacion_prom,
        {{ safe_divide('sum(ley_concentrado_cu_pct * tonelaje_hora_ton)', 'sum(tonelaje_hora_ton)') }} as ley_concentrado_prom,
        {{ safe_divide('sum(ley_cola_cu_pct * tonelaje_hora_ton)', 'sum(tonelaje_hora_ton)') }} as ley_cola_prom
    from {{ ref('stg_flotation') }}
    group by 1, 2, 3
),

seguridad_agg as (
    select
        fecha,
        turno,
        faena,
        count(*) as total_incidentes,
        count(*) filter (where severidad in ('GRAVE', 'FATAL')) as incidentes_graves_fatales,
        sum(horas_detencion_asociadas) as horas_detencion_seguridad,
        sum(
            case severidad
                when 'LEVE' then 1
                when 'GRAVE' then 5
                when 'FATAL' then 25
                else 0
            end
        ) as puntaje_riesgo
    from {{ ref('stg_safety') }}
    group by 1, 2, 3
),

combinado as (
    select
        e.fecha,
        e.turno,
        e.faena,
        e.n_camiones_activos,
        e.disponibilidad_promedio,
        e.desempeno_promedio,
        e.horas_turno_totales,
        e.tonelaje_transportado_total,
        f.tonelaje_procesado_total,
        f.ley_alimentacion_prom,
        f.ley_concentrado_prom,
        f.ley_cola_prom,
        coalesce(s.total_incidentes, 0) as total_incidentes,
        coalesce(s.incidentes_graves_fatales, 0) as incidentes_graves_fatales,
        coalesce(s.horas_detencion_seguridad, 0) as horas_detencion_seguridad,
        coalesce(s.puntaje_riesgo, 0) as puntaje_riesgo_operacional
    from equipo_agg e
    left join flotacion_agg f
        on e.fecha = f.fecha and e.turno = f.turno and e.faena = f.faena
    left join seguridad_agg s
        on e.fecha = s.fecha and e.turno = s.turno and e.faena = s.faena
),

final as (
    select
        *,
        {{ safe_divide('(horas_turno_totales - horas_detencion_seguridad)', 'horas_turno_totales') }} as calidad_pct
    from combinado
)

select
    fecha,
    turno,
    faena,
    n_camiones_activos,
    round(disponibilidad_promedio * 100, 2) as tiee_pct,
    round(desempeno_promedio * 100, 2) as desempeno_pct,
    round(calidad_pct * 100, 2) as calidad_pct,
    round(disponibilidad_promedio * desempeno_promedio * calidad_pct * 100, 2) as oee_pct,
    round({{ metallurgical_recovery('ley_alimentacion_prom', 'ley_concentrado_prom', 'ley_cola_prom') }}, 2) as recuperacion_cu_pct,
    round(tonelaje_procesado_total, 1) as tonelaje_procesado_total_ton,
    round(tonelaje_transportado_total, 1) as tonelaje_transportado_total_ton,
    total_incidentes,
    incidentes_graves_fatales,
    round(horas_detencion_seguridad, 2) as horas_detencion_seguridad,
    puntaje_riesgo_operacional,
    case
        when puntaje_riesgo_operacional = 0 then 'Bajo'
        when puntaje_riesgo_operacional < 5 then 'Medio'
        when puntaje_riesgo_operacional < 25 then 'Alto'
        else 'Crítico'
    end as nivel_riesgo
from final
order by fecha, faena, turno
