{#- Bucket a numeric interest rate into a product band. -#}
{% macro int_rate_band(col) -%}
case
    when {{ col }} is null then 'unknown'
    when {{ col }} < 10 then '<10%'
    when {{ col }} < 15 then '10-15%'
    when {{ col }} < 20 then '15-20%'
    when {{ col }} < 25 then '20-25%'
    else '25%+'
end
{%- endmacro %}
