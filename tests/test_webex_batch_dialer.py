import csv

from webex_batch_dialer import BatchDialer, load_call_list, normalize_e164
from webex_batch_dialer.webex_client import WebexError


def test_normalize():
    assert normalize_e164("(214) 440-2422") == "+12144402422"
    assert normalize_e164("+1 972-408-5757") == "+19724085757"
    assert normalize_e164("12345") is None


def write_csv(tmp_path, rows):
    p = tmp_path / "list.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, ["business_name", "phone_e164", "email", "state"])
        w.writeheader()
        w.writerows(rows)
    return p


def test_load_filters_dnc_dupes_invalid(tmp_path):
    p = write_csv(tmp_path, [
        {"business_name": "A", "phone_e164": "+12144402422", "state": "TX"},
        {"business_name": "A2", "phone_e164": "(214) 440-2422", "state": "TX"},
        {"business_name": "B", "phone_e164": "+14698919938", "state": "TX"},
        {"business_name": "C", "phone_e164": "bad", "state": "TX"},
    ])
    recs, warns = load_call_list(p, dnc=["+14698919938"])
    assert [r.business_name for r in recs] == ["A"]
    assert len(warns) == 3


class FakeClient:
    def __init__(self, fail=()):
        self.dialed, self.fail, self.n, self.polls = [], set(fail), 0, 0

    def dial(self, dest):
        if dest in self.fail:
            raise WebexError(400, "bad")
        self.dialed.append(dest)
        self.n += 1
        return {"callId": f"c{self.n}"}

    def active_calls(self):
        self.polls += 1
        return [{"id": f"c{self.n}", "state": "connected"}] if self.polls % 2 else []

    def hangup(self, call_id):
        pass

    def call_history(self, t):
        return [{"phoneNumber": "tel:+12144402422", "duration": 61}]


def test_run_resume_and_sync(tmp_path):
    p = write_csv(tmp_path, [
        {"business_name": "A", "phone_e164": "+12144402422", "state": "TX"},
        {"business_name": "B", "phone_e164": "+14698919938", "state": "TX"},
    ])
    recs, _ = load_call_list(p)
    c = FakeClient(fail={"+14698919938"})
    d = BatchDialer(c, recs, tmp_path / "s.jsonl", lambda r: ("connected", "ok"), sleep=lambda s: None, enforce_hours=False)
    d.run()
    assert [r.disposition for r in recs] == ["connected", "failed"]
    # resume: a fresh dialer does not redial completed numbers
    recs2, _ = load_call_list(p)
    c2 = FakeClient()
    BatchDialer(c2, recs2, tmp_path / "s.jsonl", sleep=lambda s: None, enforce_hours=False).run()
    assert c2.dialed == []
    assert d.sync_history() == 1 and recs[0].duration_s == 61
