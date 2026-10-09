# Webex batch dialer

Progressive dialer that works the **New Call List** (`phone_e164` column) through Webex Calling.
It dials one number at a time from your Webex user (the call rings your Webex client/desk phone),
waits for the call to end, asks for a disposition, then dials the next. It is not a predictive/robo-dialer.

## Setup
1. Create a Webex Integration (developer.webex.com) with scopes `spark:calls_write spark:calls_read`.
   Your Webex user needs Webex Calling.
2. Do the OAuth flow once and export:
   `WEBEX_CLIENT_ID`, `WEBEX_CLIENT_SECRET`, `WEBEX_REFRESH_TOKEN` (or a short-lived `WEBEX_ACCESS_TOKEN`).
3. Export the Google Sheet "New Call List" as CSV.

## Use
```bash
python -m webex_batch_dialer run new_call_list.csv --dry-run          # validate / preview queue
python -m webex_batch_dialer run new_call_list.csv --dnc dnc.txt --limit 10
python -m webex_batch_dialer sync new_call_list.csv                   # reconcile durations from Webex call history
```
Results go to `dialer_results.csv`; progress is checkpointed in `dialer_state.jsonl`, so a restart resumes
without redialing finished numbers.

## Safeguards
Invalid/duplicate numbers and the do-not-call file are dropped; calls only go out 9am-8pm Mon-Sat in the lead's
state timezone (`--ignore-hours` to override); ring-out after 45s. You remain responsible for TCPA/DNC
compliance (B2B numbers can still be on the National DNC registry or be mobile numbers).
