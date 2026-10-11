# New business lead pull

Weekly job (GitHub Actions: `.github/workflows/new-business-weekly.yml`, Mondays 7am Central, or run it by hand)
that pulls newly opened DFW outlets (Dallas, Collin, Denton, Tarrant, Rockwall, Kaufman, Ellis, Parker, Johnson and Wise counties) from the Texas
Comptroller's public sales-tax permit data and writes `data/new_businesses_<date>.csv` in the call-list format.

- Keeps retail, food service, personal services and arts/rec; drops chains and home/apartment addresses.
- Keeps sole proprietors that have a commercial address.
- Remembers outlets it already emitted (`data/seen_outlets.txt`), so each week only returns new ones.
- Phone, email and website come back blank: the permit data doesn't include them. Enrich, then paste into the Call Console's **Add leads** box.

Run locally: `PYTHONPATH=. python -m new_business_pipeline.permits --days 10`

Note: this commits lead files (business names and addresses) to the repo. Keep the repo private.
