# database/seed/05_membership/

No seed data. Membership records (`sangha_sevi`, `membership_sakha_affiliation`,
`parichaya_patra`, `anumati_patra`, transfer/journey/status history, renewal) are created
at runtime through the registration flow and membership management workflows.

> **Removed:** The former `01_tier4_verification_membership.sql` (SS1-SS5 sangha_sevi records
> with affiliations, documents, transfers, journey events, and status history) has been deleted.
> Real membership data is now created through the registration API (`POST /api/v1/register`).
