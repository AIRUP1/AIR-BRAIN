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


def test_headers_case_insensitive(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text('"Business Name","Phone","City"\n"Acme","+18178286326","Fort Worth"\n')
    recs, warns = load_call_list(p)
    assert warns == [] and recs[0].business_name == "Acme" and recs[0].phone_e164 == "+18178286326"


def test_inbox_auto_run_and_failure_stop(tmp_path, monkeypatch):
    from webex_batch_dialer import automation
    monkeypatch.setattr(automation, "window_open", lambda now=None: True)
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a.csv").write_text("Business Name,Phone\nA,+12144402422\nB,+14698919938\n")
    res = automation.run_inbox(FakeClient(), inbox, once=True, sleep=lambda s: None, enforce_hours=False)
    assert res[0]["called"] == 2 and res[0]["pending"] == 0
    assert (inbox / "done" / "a.csv").exists() and (inbox / "results" / "a.results.csv").exists()

    (inbox / "b.csv").write_text("Business Name,Phone\n" + "".join(f"X{i},+1214555{i:04d}\n" for i in range(8)))
    bad = FakeClient(fail={f"+1214555{i:04d}" for i in range(8)})
    import pytest
    with pytest.raises(automation.TooManyFailures):
        automation.run_inbox(bad, inbox, once=True, sleep=lambda s: None, max_failures=3, enforce_hours=False)
