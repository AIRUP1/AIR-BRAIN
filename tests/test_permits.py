import csv
from datetime import date

from new_business_pipeline.permits import HEADER, keep, outlet_key, run


def row(**kw):
    base = dict(taxpayer_number="1", outlet_number="1", taxpayer_name="ACME LLC", outlet_name="ACME TACOS", outlet_address="100 MAIN ST STE 5",
                outlet_city="PLANO", outlet_zip_code="75074", outlet_county_code="043", outlet_naics_code="722511",
                taxpayer_organization_type="CL", outlet_first_sales_date="2026-10-05T00:00:00.000")
    base.update(kw)
    return base


def test_filters():
    assert keep(row())
    assert keep(row(taxpayer_organization_type="IS"))              # sole proprietors are kept
    assert not keep(row(outlet_address="12 OAK LN APT 4"))         # home address
    assert not keep(row(outlet_name="CHIPOTLE MEXICAN GRILL #5"))  # chain
    assert not keep(row(outlet_naics_code="454110"))               # non-store retail
    assert not keep(row(outlet_naics_code="336310"))               # manufacturing


def test_run_dedupes_and_remembers(tmp_path):
    rows = [row(), row(taxpayer_number="2", outlet_name="ACME TACOS #2"), row(taxpayer_number="3", outlet_name="BEAUTY BAR", outlet_naics_code="812112")]
    out, seen = tmp_path / "o.csv", tmp_path / "seen.txt"
    assert run(date(2026, 9, 1), date(2026, 10, 9), out, seen, rows=rows) == 2   # "ACME TACOS" and "#2" collapse at same address
    data = list(csv.reader(out.open()))
    assert data[0] == HEADER and len(data) == 3
    out2 = tmp_path / "o2.csv"
    assert run(date(2026, 9, 1), date(2026, 10, 9), out2, seen, rows=rows) == 0  # nothing new the second time
    assert not out2.exists()
    assert outlet_key(rows[0]) in seen.read_text()
