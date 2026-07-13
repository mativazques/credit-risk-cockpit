-- Staging: cast, clean, rename, parse dates. One row per loan.
-- Raw dates are 'Mon-YYYY' (e.g. 'Dec-2015'); `term` is ' 36 months' / ' 60 months'.

with source as (

    select * from {{ source('lending_club', 'accepted') }}

),

renamed as (

    select
        -- keys
        id as loan_id,

        -- dates
        parse_date('%b-%Y', issue_d)      as issue_date,
        parse_date('%b-%Y', last_pymnt_d) as last_pymnt_date,

        -- term ' 36 months' -> 36
        cast(regexp_extract(term, r'(\d+)') as int64) as term_months,

        -- loan status: keep raw, plus a standardized bucket
        loan_status as loan_status_raw,
        case
            when loan_status in (
                'Charged Off',
                'Does not meet the credit policy. Status:Charged Off',
                'Default'
            ) then 'charged_off'
            when loan_status in (
                'Fully Paid',
                'Does not meet the credit policy. Status:Fully Paid'
            ) then 'fully_paid'
            when loan_status in (
                'Current', 'In Grace Period',
                'Late (16-30 days)', 'Late (31-120 days)'
            ) then 'current'
            else 'other'
        end as loan_status_std,

        -- product attributes
        grade,
        sub_grade,
        int_rate,

        -- borrower attributes (member_id is redacted/null in this public dataset,
        -- so "borrower" is modeled downstream as a junk dim of applicant attributes)
        trim(home_ownership)      as home_ownership,
        emp_length,
        verification_status,
        addr_state,
        purpose,

        -- measures
        loan_amnt,
        funded_amnt,
        installment,
        annual_inc,
        dti,
        total_rec_prncp,
        out_prncp,
        recoveries

    from source
    -- drop the handful of malformed/footer rows that survive as null keys
    where id is not null
      and issue_d is not null
      and term is not null

)

select * from renamed
