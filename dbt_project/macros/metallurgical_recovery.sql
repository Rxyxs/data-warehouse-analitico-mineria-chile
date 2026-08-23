{% macro metallurgical_recovery(feed_grade, concentrate_grade, tailings_grade) %}
    -- Formula de recuperacion metalurgica de dos productos (two-product shortcut
    -- formula), estandar en metalurgia extractiva del cobre. Valida solo cuando
    -- concentrate_grade > feed_grade > tailings_grade >= 0; en cualquier otro caso
    -- (datos inconsistentes) retorna null en vez de un porcentaje sin sentido fisico.
    (case
        when {{ feed_grade }} is null or {{ concentrate_grade }} is null or {{ tailings_grade }} is null then null
        when {{ feed_grade }} <= {{ tailings_grade }} then null
        when {{ concentrate_grade }} <= {{ tailings_grade }} then null
        else
            ({{ concentrate_grade }} * ({{ feed_grade }} - {{ tailings_grade }}))
            / ({{ feed_grade }} * ({{ concentrate_grade }} - {{ tailings_grade }}))
            * 100
    end)
{% endmacro %}
