-- Product dimension: distinct (grade, sub_grade, term, interest-rate band).

with base as (

    select distinct
        grade,
        sub_grade,
        term_months,
        {{ int_rate_band('int_rate') }} as int_rate_band
    from {{ ref('stg_loans') }}

)

select
    {{ surrogate_key(['grade', 'sub_grade', 'term_months', 'int_rate_band']) }} as loan_product_key,
    grade,
    sub_grade,
    term_months,
    int_rate_band
from base
