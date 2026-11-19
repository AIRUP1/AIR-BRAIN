"""Merchant lead records: CSV/XML in and out, phone normalization, suppression."""
from __future__ import annotations

import csv
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

FLAG_FIELDS = (
    "called",
    "connected",
    "failed",
    "voicemail",
    "interested",
    "connect_live_agent",
    "opt_out",
)

# Column order for CSV/XML output. The first four are the sheet columns the
# campaign uses; the rest record call results and provenance.
COLUMNS = (
    "merchant_business_name",
    "phone_number",
    "pos_dm",
    "owner_prequalification",
    *FLAG_FIELDS,
    "scraper_source",
    "research_summary",
    "session_id",
    "notes",
)

HEADER_ALIASES = {
    "merchant_business_name": "merchant_business_name",
    "business_name": "merchant_business_name",
    "merchant": "merchant_business_name",
    "phone": "phone_number",
    "phone_number": "phone_number",
    "pos_dm": "pos_dm",
    "pos": "pos_dm",
    "dm": "pos_dm",
    "owner_pre_qualification": "owner_prequalification",
    "owner_prequalification": "owner_prequalification",
    "owner": "owner_prequalification",
    "connect_live_agent": "connect_live_agent",
    "live_agent": "connect_live_agent",
    "scraper": "scraper_source",
    "scraper_source": "scraper_source",
    "source": "scraper_source",
}

TRUE_VALUES = {"1", "true", "yes", "y", "x", "t"}


class LeadFileError(ValueError):
    """Raised for unreadable or unsafe lead files."""


@dataclass
class Lead:
    merchant_business_name: str = ""
    phone_number: str = ""
    pos_dm: str = ""
    owner_prequalification: str = ""
    called: bool = False
    connected: bool = False
    failed: bool = False
    voicemail: bool = False
    interested: bool = False
    connect_live_agent: bool = False
    opt_out: bool = False
    scraper_source: str = ""
    research_summary: str = ""
    session_id: str = ""
    notes: str = ""

    def to_row(self) -> Dict[str, str]:
        row: Dict[str, str] = {}
        for name in COLUMNS:
            value = getattr(self, name)
            row[name] = ("yes" if value else "") if isinstance(value, bool) else str(value)
        return row


def normalize_header(header: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")
    return HEADER_ALIASES.get(key, key)


def normalize_phone(raw: str) -> Optional[str]:
    """Return an E.164 number, or None when it cannot be one.

    Ten digits and eleven digits starting with 1 are treated as US/Canada.
    Anything else must already carry a leading + and 7-15 digits.
    """
    text = (raw or "").strip()
    digits = re.sub(r"\D", "", text)
    if text.startswith("+"):
        return "+" + digits if 7 <= len(digits) <= 15 and digits[0] != "0" else None
    if len(digits) == 10 and digits[0] in "23456789":
        return "+1" + digits
    if len(digits) == 11 and digits[0] == "1" and digits[1] in "23456789":
        return "+" + digits
    return None


def _as_bool(value: object) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def _lead_from_mapping(raw: Dict[str, str]) -> Lead:
    values: Dict[str, object] = {}
    for header, value in raw.items():
        if header is None:
            continue
        name = normalize_header(header)
        if name in COLUMNS:
            values[name] = (value or "").strip()
    lead = Lead()
    for f in fields(Lead):
        if f.name not in values:
            continue
        value = values[f.name]
        setattr(lead, f.name, _as_bool(value) if f.name in FLAG_FIELDS else value)
    return lead


def read_csv(path: Path) -> List[Lead]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [_lead_from_mapping(row) for row in csv.DictReader(handle)]


def read_xml(path: Path) -> List[Lead]:
    data = Path(path).read_bytes()
    head = data[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise LeadFileError("XML with DOCTYPE or ENTITY declarations is not accepted")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise LeadFileError(f"Invalid XML: {exc}") from exc
    return [
        _lead_from_mapping({child.tag: child.text or "" for child in node})
        for node in root.iter("lead")
    ]


def load_leads(path: str | Path) -> List[Lead]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv(path)
    if suffix == ".xml":
        return read_xml(path)
    raise LeadFileError(f"Unsupported lead file type: {suffix or path.name}")


def write_csv(leads: Iterable[Lead], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS))
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_row())


def write_xml(leads: Iterable[Lead], path: Path) -> None:
    root = ET.Element("leads")
    for lead in leads:
        node = ET.SubElement(root, "lead")
        for name, value in lead.to_row().items():
            ET.SubElement(node, name).text = value
    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def save_leads(leads: Iterable[Lead], path: str | Path) -> None:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        write_csv(leads, path)
    elif suffix == ".xml":
        write_xml(leads, path)
    else:
        raise LeadFileError(f"Unsupported output type: {suffix or path.name}")


def clean_leads(leads: Iterable[Lead]) -> tuple[List[Lead], List[str]]:
    """Normalize phones and drop duplicates. Returns (leads, problems)."""
    seen: Set[str] = set()
    kept: List[Lead] = []
    problems: List[str] = []
    for index, lead in enumerate(leads, start=1):
        phone = normalize_phone(lead.phone_number)
        label = lead.merchant_business_name or f"row {index}"
        if not lead.merchant_business_name.strip():
            problems.append(f"{label}: missing merchant business name")
            continue
        if phone is None:
            problems.append(f"{label}: invalid phone '{lead.phone_number}'")
            continue
        if phone in seen:
            problems.append(f"{label}: duplicate of {phone}")
            continue
        seen.add(phone)
        lead.phone_number = phone
        kept.append(lead)
    return kept, problems


def load_suppression(path: str | Path | None) -> Set[str]:
    """One number per line; blank lines and # comments are ignored."""
    if not path:
        return set()
    numbers: Set[str] = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        normalized = normalize_phone(line) if line else None
        if normalized:
            numbers.add(normalized)
    return numbers


def callable_reason(
    lead: Lead, suppression: Set[str], retry: bool = False
) -> Optional[str]:
    """Return why a lead must not be dialed, or None when it is eligible."""
    if lead.opt_out:
        return "opted out"
    if lead.phone_number in suppression:
        return "on suppression (do-not-call) list"
    if normalize_phone(lead.phone_number) is None:
        return "invalid phone"
    if lead.called and not retry:
        return "already called"
    if lead.connected or lead.interested:
        return "already reached"
    return None
