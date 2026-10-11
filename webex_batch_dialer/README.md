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
state timezone (`--ignore-hours` to override); ring-out (auto hang-up) after 5s. You remain responsible for TCPA/DNC
compliance (B2B numbers can still be on the National DNC registry or be mobile numbers).

## Getting the refresh token
In a cloud terminal (Codespaces, github.dev, SSH) use `python -m webex_batch_dialer.get_webex_token --manual`: open the printed link in your own browser, sign in, then paste the address of the page it lands on (it will say it can't connect; that's expected).

Create the Integration with redirect URI `http://localhost:3000/callback`, then run
`python -m webex_batch_dialer.get_webex_token`, sign in as your Webex Calling user, and copy the
printed `export` lines into your shell profile or secrets store. Never commit them.

## Hands-off mode (`auto`)
```bash
mkdir inbox                      # drop call-list CSVs here (any headers like "Business Name", "Phone")
python -m webex_batch_dialer auto inbox            # keeps running; picks up new files as they appear
python -m webex_batch_dialer auto inbox --once     # process what's there and exit (for cron)
```
- Dials only 9a-8p CT Mon-Sat and waits otherwise; resumes mid-file the next day.
- Logs outcomes automatically from Webex state (answered = connected, otherwise no_answer). Notes can be added later.
- Finished files move to `inbox/done/`; results are in `inbox/results/<file>.results.csv`.
- Stops with exit code 3 if 5 dials in a row fail (`--max-failures N`), e.g. an expired token or a Webex outage.
- A person still takes the calls: Webex rings your device and you talk when someone picks up.

Cron example (every 15 minutes, weekdays): `*/15 9-19 * * 1-6 cd /path/to/AIR-BRAIN && python -m webex_batch_dialer auto inbox --once`
(set the `WEBEX_*` variables in the crontab or a wrapper script).

## Run from GitHub Actions
1. Repo -> Settings -> Secrets and variables -> Actions -> New repository secret. Add `WEBEX_CLIENT_ID`,
   `WEBEX_CLIENT_SECRET`, `WEBEX_REFRESH_TOKEN` (values from `get_webex_token`). Never put them in files.
2. Put call-list CSVs in `dialer_inbox/` (only in a **private** repo; they contain business phone numbers).
3. Actions -> "Webex dialer (manual)" -> Run workflow. It runs one pass and uploads `dialer-results`.
The workflow is manual on purpose (each dial rings your Webex device). Webex refresh tokens expire after
about 90 days, so re-run `get_webex_token` and update the secret when the run reports an auth error.

## Scheduled batches on GitHub (opt-in)
`.github/workflows/webex-dialer-scheduled.yml` runs every 30 minutes, dials up to `DIALER_BATCH` leads
(default 10) from `dialer_inbox/`, commits progress, and stops when everything is done.
It does nothing until you create the repo variable `DIALER_AUTORUN=true`. Delete it to stop.
Finished files move to `dialer_inbox/done/`, results go to `dialer_inbox/results/`. Keep the repo private.
Each dial rings your Webex device, so only turn it on while you can take the calls.
