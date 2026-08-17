# NSS ERP Sevak Sangha Business Rules

Document ID: SOL-SEV-004
Version: 5.0.0
Status: FROZEN (Eligibility + Lifecycle + Operations + Events + Cancellation) / PARTIALLY FROZEN (Executive + Training)

---

# 1. Institutional Rules

## SEV-001 — NSS Institution
## SEV-002 — Training Organization
## SEV-003 — Volunteer Organization
## SEV-004 — Service Organization
## SEV-005 — Leadership Development

---

# 2. Organizational Nature

## SEV-006 — Not a Membership Category
No SEVAK as NSS Membership Type.

## SEV-007 — Not a Governance Body
Sevak Sangha itself is not Governing Body.

## SEV-008 — Governance May Exist Within
Executive body uses common Governance framework.

---

# 3. Membership Rules

## SEV-009 — Common NSS Membership applies.
## SEV-010 — Sangha Sevi ID is authoritative.
## SEV-011 — No separate Membership identity.
## SEV-012 — Types remain PROBATIONARY, REGULAR, ASSOCIATE.

---

# 4. Eligibility (FROZEN)

## SEV-013 — Category Eligibility

Only the following persons are eligible:

1. Interested NSS Members
2. Existing Sevaks

NSS Membership is mandatory. No non-member may be registered.
Youth, Teenagers, Students are NOT independent eligibility categories.

## SEV-014 — Age Eligibility

No additional age restriction beyond NSS Membership eligibility.
No min_age or max_age in the database.

---

# 5. Enrollment (FROZEN)

## SEV-015 — Direct Enrollment

Eligible NSS Member directly enrolled without application-review workflow.
No separate approval required. Enrollment recorded and audited.
Does not create new NSS Membership.
An authorized user performs the registration action.

---

# 6. Participation Status (FROZEN)

## SEV-016 — Status Values

Only two statuses: ACTIVE, INACTIVE.
No PROBATIONARY_SEVAK, REGULAR_SEVAK, COMPLETED, or WITHDRAWN.
Every participation has a start_date.

---

# 7. Inactivation Rules (FROZEN)

## SEV-017 — No Automatic Inactivity

System must NOT automatically change ACTIVE to INACTIVE based on non-attendance.
No attendance-based automatic inactivity trigger exists.
Authorized person decides manually.

## SEV-021 — Mandatory Inactivation Reason

When ACTIVE is changed to INACTIVE, reason is mandatory.

Inactivation Source: MANUAL
Reasons:
- NO_LONGER_PARTICIPATING
- PERSONAL_REASON
- LONG_TERM_ABSENCE
- OTHER

Inactivation Source: SYSTEM
Reasons:
- TRANSFERRED_TO_OTHER_SAKHA (triggered by NSS Membership Transfer)
- DECEASED (triggered by Person/Membership death)

Database should have inactivation_source field (SYSTEM / MANUAL).
System-generated inactivation requires no manual intervention.

## SEV-022 — Death-Triggered Inactivation

When Person/Membership is marked DECEASED, Sevak participation automatically INACTIVE.
Reason = DECEASED. Source = SYSTEM. No manual Sevak approval required.
Death is a global Person lifecycle event (see SOL-LIFE-002).

---

# 8. Reactivation Rules (FROZEN)

## SEV-024 — Sevak Reactivation

Reactivation (INACTIVE to ACTIVE) is manual/authorized.
No reason is mandatory for reactivation.
Attendance does NOT automatically reactivate.
Reactivation action must be audited.
Previous history remains unchanged.

## SEV-025 — Reactivation Review Cycle

1. INACTIVE Sevak attends -> reactivation review cycle created.
2. Only one OPEN review cycle per Sevak at a time.
3. Additional attendance while cycle is OPEN attaches to existing cycle (no duplicates).
4. Authorized user reviews the open cycle.
5. Reviewer may: keep INACTIVE, or reactivate to ACTIVE.
6. No reason mandatory for reactivation.
7. Once reviewed, cycle is CLOSED.
8. Closed cycle remains permanently in history.
9. If still INACTIVE and attends again after cycle closed, new cycle may open.
10. Attendance never automatically changes status.

### Inactivation vs Reactivation Summary

| Action | Authorization | Reason |
|--------|--------------|--------|
| ACTIVE to INACTIVE (manual) | Authorized user | Mandatory |
| ACTIVE to INACTIVE (Transfer) | System | System-generated |
| ACTIVE to INACTIVE (Death) | System | System-generated |
| INACTIVE to ACTIVE (reactivation) | Authorized user | Not required |

---

# 9. Transfer Rules (FROZEN)

## SEV-018 — Follows NSS Membership Sakha

Sevak association subordinate to Member's current NSS Sakha.
No independent Sevak transfer workflow.
NSS Membership Transfer is authoritative.

When NSS Membership transfers Sakha A to Sakha B:
- Old participation: automatically INACTIVE, reason = TRANSFERRED_TO_OTHER_SAKHA, source = SYSTEM
- If Sakha B has Sevak Sangha: new ACTIVE participation may be created
- If Sakha B has no Sevak Sangha: no new participation created

No manual Sevak intervention required for transfer.
Historical records preserved permanently.

## SEV-019 — No Sevak Sangha in Current Sakha

If current Sakha has no Sevak Sangha:
- No current Sevak association exists
- Previous history preserved as historical only
- Members do NOT attend another Sakha's Sevak Sangha
- No cross-Sakha Sevak participation

---

# 10. Operational Model (FROZEN)

## SEV-023 — Two Operational Levels

### Sakha-Level Sevak Sangha
- A Sakha MAY or MAY NOT have a Sevak Sangha
- Where it exists, sessions generally after Sunday Sangha Puja
- Frequency not fixed (depends on individual Sakha)
- Not necessarily every Sunday

### Anchalika/Zilla-Level Sevak Sangha Puja
- Organized at Anchalika/Zilla level
- Typically once every ~6 months (configurable)
- Hosted at different Sakha Sanghas within that Anchalika/Zilla
- Host Sakha is venue only, not a membership change

No formal training hierarchy exists.
Previously proposed training tables are NOT frozen.

---

# 11. Attendance Rules (FROZEN)

## SEV-024 — Status Does Not Prohibit Attendance

INACTIVE Sevak may still attend Sevak Sangha events.
ACTIVE does not mean must attend.
Participation status and attendance are separate concepts.

## SEV-025 — Attendance by INACTIVE Sevak

When an INACTIVE Sevak attends:
1. Attendance recorded normally
2. Status NOT automatically changed
3. System flags for Reactivation Review (see section 8)
4. Authorized user decides via review cycle

No automatic: INACTIVE + ATTENDANCE = ACTIVE

## SEV-026 — No Automatic Reactivation

Attendance never automatically reactivates a Sevak.
Reactivation requires authorized human decision via review cycle.

## SEV-027 — Inactivity Threshold WITHDRAWN

Previously proposed 2-month inactivity threshold is WITHDRAWN.
Not appropriate given 6-month Anchalika/Zilla event cycle and variable Sakha frequency.
No attendance-based automatic inactivity trigger exists.

---

# 12. Event Eligibility (FROZEN)

## SEV-028 — Anchalika/Zilla Puja Eligibility

System auto-populates eligible participant list:
1. All eligible Sevaks in that Anchalika/Zilla
2. Male NSS Members of that Anchalika/Zilla

No pre-registration required. Eligibility derived from authoritative records.
Each person appears once (deduplicated).
Eligibility does not equal attendance.

## SEV-029 — Sakha-Level Session Eligibility

Same broad eligibility as Anchalika/Zilla:
1. All eligible Sevaks of that Sakha
2. Male NSS Members of that Sakha

One person = one participant entry. Deduplicated.
Eligibility does not equal attendance.

## SEV-030 — Unique Participant Rule

Each eligible person appears only once per event regardless of how many criteria met.
One attendance record per person per event.

---

# 13. Event Scheduling (FROZEN)

## SEV-031 — Manual Event Creation and Host

No fixed recurring schedule enforced.
Events created by authorized user when required.
No automatic recurring event generation.

Event types:
- Sakha-level Sevak Sangha Session
- Anchalika/Zilla-level Sevak Sangha Puja

Every event requires a registered Sakha as host.
Event uses host Sakha's registered location (no separate venue override).
Location snapshot stored at event creation for historical integrity.

Event lifecycle:
- DRAFT (not visible, no notifications)
- PUBLISHED/CONFIRMED (visible on dashboards, notifications sent)

Notification and dashboard visibility only on PUBLISHED/CONFIRMED.
Respective Sanghas notified after publication.

---

# 14. Event Visibility and Intention (FROZEN)

## SEV-032 — Cross-Anchalika/Zilla Attendance

A Sevak from another Anchalika/Zilla may attend a published event.
Attendance recorded without changing organizational affiliation.
No membership transfer or Sangha transfer occurs.

## SEV-033 — Event Attendance Intention

Members may optionally indicate intention:
- INTERESTED / WILL ATTEND
- I WONT BE ATTENDING

Response is optional, changeable before event.
No response is valid (not interpreted as wont attend).
Intention does NOT constitute attendance.
Intention does NOT restrict attendance.
Purpose: organizational planning (seating, food, transport).

Four distinct concepts:
- Eligibility (auto-generated)
- Visibility (dashboard)
- Intention (optional response)
- Attendance (actual participation)

These are all separate and never interchangeable.

---

# 15. Probable Attendance (FROZEN)

## SEV-034 — Probable Attendance View

Host Sangha sees both probable count AND individual participant list.

Probable Attendance includes:
1. All Sevak Members (ACTIVE + INACTIVE) — automatically included
2. Host Sakha's male NSS Members — automatically included (no "I'll Attend" needed)
3. Other eligible male NSS Members who marked "I'll Attend"

Excludes:
- Sevaks who explicitly marked "I wont attend"
- Non-Sevak members who did not respond
- Non-Sevak members who marked "I wont attend"

All deduplicated by person.

Actual attendance NOT limited to probable list — system can record anyone who attends.

Three distinct numbers for host:
- Total Eligible
- Probable Attendance
- Actual Attendance

These are never interchangeable.

---

# 16. Administrative Authority (FROZEN)

## SEV-032 — Existing ERP RBAC

Uses existing NSS ERP RBAC + organizational scope.
No separate Sevak permission architecture at this stage.

Scope:
- Sakha-level user: Sakha-level Sevak operations
- Anchalika-level user: Anchalika operations
- Zilla-level user: Zilla operations
- Kendra-level user: Kendra oversight

Actions covered:
- Direct Sevak enrollment
- Manual ACTIVE to INACTIVE
- Inactivity reason entry
- Reactivation review
- INACTIVE to ACTIVE
- Sakha-level session management
- Anchalika/Zilla Puja management
- Event creation (DRAFT and PUBLISHED)

No specific office-bearer titles hard-coded as having permissions.
Detailed permission matrix defined centrally in Administration/RBAC module.

---

# 17. Common Lifecycle References

Transfer and Death inactivation follow:
- SOL-LIFE-001 (Participation Lifecycle Rules)
- SOL-LIFE-002 (Person Lifecycle Rules)

Sangha association follows current NSS Sakha — applies identically to Sevak, Mahila, Kumari.

---

# 18. Governance Rules (PENDING)

Executive positions: PENDING
Selection/Election: PENDING
Term Duration: PENDING
Body type: SEVAK_SANGHA_EXECUTIVE (provisional, uses Unified Governance Model)

---

# 19. Training Rules (REVISED)

No formal training hierarchy exists.
No Orientation -> Basic -> Advanced -> Leadership progression.
Training may exist as future optional capability but is NOT a mandatory lifecycle.
Previously proposed training tables are NOT frozen.

---

# 20. History and Audit

Historical milestones preserved (1973, 1987, 1991).
Auditability required for all status changes, enrollment, and event actions.
Physical deletion prohibited.

---

# 21.5. Event Cancellation and Rescheduling (FROZEN)

## SEV-035 — Cancellation and Rescheduling

A published/confirmed event may be cancelled or rescheduled.

### Cancellation
- Status changes to CANCELLED.
- Event preserved historically.
- Members and Sanghas notified.
- Removed from upcoming views.
- No new attendance after cancellation.
- Existing intention responses remain historical.
- Cancellation audited.

### Rescheduling
- Same event identity retained.
- New date/time recorded.
- Complete rescheduling history preserved.
- Members notified of new date.
- Intention responses must be reconfirmed for new date.
- Previous intentions remain as historical records (not overwritten).
- Probable attendance recalculated from current information.

## SEV-036 — Post-Start Cancellation and Rescheduling

Cancellation or rescheduling permitted before OR after event start time.

If after start:
- All attendance already recorded is permanently preserved.
- Cancelled event does not accept attendance after cancellation effective time.
- Rescheduled event retains identity and preserves original + revised history.

Audit required for all post-start changes:
- Original status, Changed status
- Change date/time, Changed by
- Reason/remarks
- Previous date/time

### Event Lifecycle

DRAFT -> PUBLISHED/CONFIRMED -> CANCELLED or RESCHEDULED -> (if rescheduled) New Date -> Reconfirm Intention -> Event Occurs -> Attendance -> Reconciliation -> COMPLETED

Historical identity and recorded attendance are never destroyed.

## SEV-037 — Event Completion and Closure

Event becomes eligible for completion after scheduled end time.
Event stays open for attendance reconciliation (not immediately locked).

Organizer may:
- Complete attendance marking
- Add legitimate attendees not in probable list
- Correct attendance records
- Reconcile actual attendance
- Ensure INACTIVE Sevak attendance generates reactivation-review flag

Manual completion: authorized organizer marks COMPLETED.
Automatic closure: system auto-closes after configurable post-event period (not hard-coded).

Once COMPLETED:
- Event permanently available in history
- Attendance preserved
- Intention responses historical
- Probable attendance available for comparison
- Event statistics finalized
- Normal editing restricted per audit/admin rules

Completion never deletes: Event, Attendance, Intentions, Participant history, Reactivation reviews, Host Sakha, Location, Scheduling history, Notifications, Audit trail.

## SEV-038 — Post-Event Reconciliation Period

After event ends, enters reconciliation period.
Organizer can mark COMPLETED anytime once reconciliation finished.
System has configurable maximum post-event reconciliation period (not hard-coded).
If organizer does not complete within max period, system auto-completes.

During reconciliation: complete missing attendance, add legitimate attendees, correct errors, review probable vs actual, ensure INACTIVE attendance generates reactivation review.

After COMPLETED: closed for normal editing. Post-completion corrections go through centralized ERP correction/audit mechanism.

## SEV-039 — Post-Completion Correction Workflow

Once COMPLETED, attendance and event records locked for normal editing.
Corrections only through approval workflow.

Approval matrix:
- Sakha Admin initiates: Secretary + President approval required
- Secretary initiates: President approval required
- President initiates: event-dependent (see SEV-040)
- Requester cannot approve own correction

Every correction preserves:
- Original value
- Requested value
- Reason for correction
- Requested by + timestamp
- Approver(s) + approval timestamp
- Final change
- Audit trail

Original value never disappears from history.

## SEV-040 — President-Initiated Correction Authority

President-initiated post-completion correction approval is event-dependent.
No universal self-approval or higher-approval hard-coded.

Approval framework must support:
- Event Type
- Organizational Level
- Requester Role
- Required Approver Role(s)
- Approval Sequence

Specific President rules finalized when governance authority matrix is defined.

## SEV-041 — Member-Facing Event Results

After event COMPLETED, ERP may display generic event information to members:
- Event Name, Date, Type, Host Sakha, Location, Organizing Anchalika/Zilla
- General participation/attendance summary

Detailed attendance/result visibility NOT frozen at this stage.
Individual attendance details, reports, analytics, correction history subject to role-based access and future Reports/Event/Privacy/RBAC standards.

Members may receive generic completed event info. Detailed visibility governed by common standards (to be defined).

## SEV-042 — Sevak Enrollment and Sakha Association Dates

Two separate dates maintained:

### First Sevak Enrollment Date
- Date person was first enrolled as a Sevak.
- Permanent. Never changes on transfer or reactivation.
- Represents beginning of overall Sevak history.

### Sakha Association History
- Effective-dated records of Sakha associations.
- Current Sakha Association derived from active history record.
- Changes only when NSS Membership Sakha changes and corresponding Sevak Sangha exists.

Example:
- First enrollment: 01-Jan-2020 at Sakha A
- Transfer: 15-Aug-2026 to Sakha B
- History preserves: Sakha A (2020-2026), Sakha B (2026-current)
- First Enrollment Date remains 01-Jan-2020

Reactivation retains original First Sevak Enrollment Date.

## SEV-043 — Seva Assignment and Approval

Sevak Seva participation is separate from Sevak ACTIVE/INACTIVE status.

An enrolled Sevak should undertake Seva under an approved Seva Category.

### Regular Sakha Seva Approval Chain
Sevak -> Seva Category -> Seva Head Approval -> Sakha President Approval -> Approved Assignment

### UPBS Seva Approval Chain
Sevak -> UPBS Seva Category -> UPBS Seva Head -> Kendra Submission -> Parichalak/President Approval -> Approved Assignment

### Key Rules
- Sevak status (ACTIVE/INACTIVE) is separate from Seva Assignment status
- ACTIVE Sevak does not mean automatically approved for every Seva
- INACTIVE Sevak does not mean Seva assignment automatically deleted
- Seva Categories are master-data driven (not hard-coded)
- One Sevak may have multiple Seva Assignments
- Relationship: Sevak ->< Seva Assignment >-> Seva Category
- Approval information attached to each assignment
- Seva Assignment has its own lifecycle

## SEV-044 — Seva Category Request and Assignment

Seva assignment may originate from:
1. SEVAK_REQUEST: Sevak selects/requests Seva Category -> Seva Head Review -> Approval/Rejection
2. SEVA_HEAD_RECOMMENDATION: Seva Head recommends/assigns -> Sevak Review -> Approval

If rejected: Sevak may request another category. Rejected request remains in history.

Regular Sakha approval: Seva Head -> Sakha President
UPBS approval: UPBS Seva Head -> Kendra -> Parichalak/President

Origin (request_source) tracked: SEVAK_REQUEST or SEVA_HEAD_RECOMMENDATION
Request and approved assignment are separate concepts.

## SEV-045 — Multiple Seva Assignments

A Sevak may have multiple active Seva assignments simultaneously.

Each assignment independently has:
- Seva Category
- Request/recommendation origin
- Approval workflow
- Approval authority
- Assignment status
- Effective date
- End/history info
- Audit trail

Approval of one does not auto-approve another.
Rejection/inactivation of one does not change overall Sevak status or other assignments.
Sevak may hold Sakha Seva + UPBS Seva simultaneously.

Sevak status (ACTIVE/INACTIVE) is separate from individual Seva assignment status.

## SEV-046 — Seva After NSS Membership Transfer

NSS Membership Transfer changes current Sakha.
Does not create independent Sevak transfer workflow.

Sakha-specific Seva: old assignments become historical (preserved permanently).
Sevak may apply for new Seva in new Sakha through normal approval workflow.

UPBS Seva: not automatically terminated on transfer.
Continuation/change follows applicable UPBS/Kendra rules separately.

Transfer does not delete Seva history.

## SEV-047 — Sevak Sangha Participation vs Seva Eligibility

Two completely separate concepts:

### Sevak Sangha Participation
- Male participants only
- Governs Sevak Sangha sessions/Puja attendance

### Seva Assignment
- NOT gender-restricted
- Male or Female NSS Members may undertake Seva
- Subject to applicable Seva category and approval process

Sevak Sangha participant eligibility does NOT restrict Seva assignments.
Female NSS Members cannot attend Sevak Sangha sessions but MAY be assigned Seva.

Seva Category Master may have its own eligibility criteria per category (not inherited from Sevak Sangha gender rule).

## SEV-048 — Seva Assignment Review on Sevak Inactivation

When Sevak becomes INACTIVE, existing Seva assignments NOT automatically terminated.
System flags each active assignment for review.

Each assignment independently reviewed by applicable Seva authority:
- Sakha Seva: reviewed by Seva Head + Sakha President
- UPBS Seva: reviewed by UPBS/Kendra authority

Authority decides per assignment: Continue or End/Inactive.

INACTIVE Sevak does NOT mean all Seva = INACTIVE.
Sevak Sangha status and Seva Assignment status remain separate.

### Event Type Distinction

Two separate event types in the ERP:
- SAKHA_SEVAK_SANGHA_SESSION (local Sakha activity, frequency varies)
- ANCHALIKA_ZILLA_SEVAK_SANGHA_PUJA (larger periodic gathering, ~6 months)

These are distinct in attendance, notifications, eligibility, reporting, and dashboards.

---

# 21. Frozen Principles

- NSS Institution
- Training/Volunteer/Service/Leadership Organization
- Not Membership Type
- NSS Membership Mandatory
- No Additional Age Restriction
- Direct Enrollment
- ACTIVE / INACTIVE Only
- Manual Inactivation with Mandatory Reason
- Transfer and Deceased Are System-Generated
- Follows NSS Membership Sakha
- No Independent Sevak Transfer
- No Cross-Sakha Sevak Participation (for Sakha-level)
- Cross-Anchalika/Zilla Attendance Permitted (for larger events)
- Two Operational Levels (Sakha + Anchalika/Zilla)
- Event Frequency Configurable, Not Hard-Coded
- Host Sakha Required for Events
- Event Lifecycle: DRAFT then PUBLISHED/CONFIRMED
- Events Can Be CANCELLED or RESCHEDULED (before or after start)
- Rescheduling Requires Intention Reconfirmation
- Post-Start Cancellation Preserves Existing Attendance
- Post-Event Reconciliation Window Before Closure
- Manual or Auto Completion (configurable period)
- Post-Completion Corrections Via Centralized Audit Only
- Correction Requires Approval (requester cannot self-approve)
- President Correction Authority Is Event-Dependent
- First Sevak Enrollment Date Is Permanent
- Reactivation Retains Original Enrollment Date
- Sakha Association Modeled As Effective-Dated History
- Seva Assignment Separate From Sevak Status
- Seva Categories Are Master-Data Driven
- Seva Approval: Seva Head + President (Sakha) or Seva Head + Kendra (UPBS)
- Seva Can Originate From Sevak Request or Seva Head Recommendation
- Multiple Active Seva Assignments Allowed Simultaneously
- Seva Assignment Status Independent From Sevak Status
- Seva After Transfer: Old Sakha Seva Historical, New Sakha Requires Fresh Application
- UPBS Seva Not Auto-Terminated on Transfer
- Sevak Sangha Participation = Male Only
- Seva Assignment = Not Gender-Restricted (Male or Female)
- Sevak Inactivation Triggers Seva Assignment Review (not auto-termination)
- Two Distinct Event Types: SAKHA_SESSION and ANCHALIKA_ZILLA_PUJA
- INACTIVE Does Not Prohibit Attendance
- Attendance Does Not Auto-Reactivate
- Reactivation Review Cycle for INACTIVE Attendance
- Reactivation Does Not Require Reason
- No Attendance-Based Inactivity Trigger
- Auto Eligibility for Events (Sevaks + Male NSS Members)
- Host Sakha Male Members Automatically Included
- One Person = One Participant Per Event
- Manual Event Creation
- Optional Attendance Intention for Planning
- Probable Attendance: Sevaks + Host Males + Others Who Respond
- Actual Attendance Not Limited to Probable List
- Existing ERP RBAC for Administration
- History Preserved
- No Unresolved Rule Hard-Coded

---

# 22. Still Pending

- Executive Structure / Positions
- Selection / Election Model
- Term Duration
- Training (optional future capability)
- Certification / Recognition
- Kishore to Sevak Transition details

---

# End of Document
