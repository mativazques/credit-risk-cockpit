-- Month-grain calendar dimension. Range covers the earliest origination
-- (2007-06) through the latest possible maturity (2018-12 issue + 60 months),
-- so it also serves the month-on-book spine in fct_loan_month.

with months as (

    select date_month
    from unnest(generate_date_array('2007-06-01', '2024-12-01', interval 1 month)) as date_month

)

select
    cast(format_date('%Y%m', date_month) as int64) as date_key,
    date_month,
    extract(year    from date_month) as year,
    extract(quarter from date_month) as quarter,
    extract(month   from date_month) as month,
    concat(cast(extract(year from date_month) as string), '-Q',
           cast(extract(quarter from date_month) as string)) as year_quarter,
    format_date('%b-%Y', date_month) as month_label
from months
