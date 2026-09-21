# BrandForge Campaign Studio — Availability Release Tracker

## Completed Delivery

- [x] Added recurring, technician-local availability windows with weekday, start/end minute, and IANA time-zone fields.
- [x] Reviewed and applied the non-destructive `technician_availability` migration.
- [x] Added brand-scoped availability reads and replacement writes.
- [x] Added a server-side availability assessment that requires the requested appointment to fit entirely inside a saved working window.
- [x] Added server-enforced collision detection for overlapping `scheduled` and `confirmed` appointments; completed and cancelled records do not block time.
- [x] Serialized appointment creation behind an active-technician row lock and repeated the collision check immediately before insertion.
- [x] Added a recurring availability editor with day controls, time-zone selection, current-coverage display, and dispatcher-facing availability guidance.
- [x] Disabled the scheduling action when a proposed service is unavailable or conflicts with an existing active appointment.
- [x] Invalidated the client-side availability query after a successful booking so the next scheduling attempt reflects the new conflict immediately.
- [x] Updated the reusable `brandforge-pos-scheduling` skill with availability and overlap-prevention requirements.
- [x] Validated the live workflow with Jordan Lee: saved weekday coverage, scheduled a two-hour Tuesday appointment, then verified that an overlapping 3:30 PM request was blocked.
- [x] Passed type-check, 17 automated tests, production build, browser console review, and skill validation.

## Operational Boundary

- [x] Availability and appointments remain operational dispatch records. They do not collect payment data, trigger a payment, or represent authorization, settlement, or completion of a Deluxe/Eliot transaction.
