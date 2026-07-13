-- Borrower dimension. NOTE: LendingClub redacts `member_id` (100% null) in this
-- public release, so there is no stable person key. This is therefore a JUNK
-- DIMENSION of applicant attributes, not a per-person dimension — honest by design.

with base as (

    select distinct
        home_ownership,
        emp_length,
        verification_status,
        addr_state
    from {{ ref('stg_loans') }}

)

select
    {{ surrogate_key(['home_ownership', 'emp_length', 'verification_status', 'addr_state']) }} as borrower_key,
    home_ownership,
    emp_length,
    verification_status,
    addr_state
from base
