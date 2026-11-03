"""Parsing helpers for the Coin History screen.

The Android build renders a transaction as a group of text/content-description
nodes. The accessibility tree is not stable enough for one fixed XPath, so the
page object feeds visible labels to these helpers and the helpers extract the
transaction type, direction, amount, timestamp and (when shown) the updated
coin balance.

The functions are deliberately free of Selenium/Appium imports so they can be
unit-tested without a device.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from config.settings import CoinSettings


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

_SPACE_RE = re.compile(r"[\s\u00a0\u2022\u00b7]+")
_BULLET_RE = re.compile(r"[•·|]+")


def normalize_spaces(text):
    return _SPACE_RE.sub(" ", str(text or "")).strip()


def normalize_key(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _lines(text):
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Dates and times
# ---------------------------------------------------------------------------

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_SLASH = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_DATE_DMY = re.compile(
    rf"\b(\d{{1,2}})\s+({_MONTH_PATTERN})[,]?\s*(\d{{2,4}})\b",
    re.I,
)
_DATE_MDY = re.compile(
    rf"\b({_MONTH_PATTERN})\s+(\d{{1,2}})[,]?\s*(\d{{2,4}})\b",
    re.I,
)
_DATE_DM = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_PATTERN})\b", re.I)
_DATE_MD = re.compile(rf"\b({_MONTH_PATTERN})\s+(\d{{1,2}})\b", re.I)
_TIME_RE = re.compile(
    r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?\b"
)


def _safe_date(year, month, day):
    try:
        return datetime(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def _normalise_year(value):
    year = int(value)
    if year < 100:
        year += 2000 if year < 70 else 1900
    return year


def parse_datetime(text, now=None):
    """Extract the transaction timestamp from a row label.

    Missing dates default to today and missing times to midnight so rows that
    only display a date can still be ordered. Returns ``None`` when the label
    contains no recognisable temporal information at all.
    """
    raw = str(text or "")
    if not raw.strip():
        return None

    now = now or datetime.now()
    lowered = raw.lower()
    base_date = None
    matched_temporal = False

    if "just now" in lowered:
        return now.replace(microsecond=0)
    if "today" in lowered:
        base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        matched_temporal = True
    elif "yesterday" in lowered:
        base_date = (now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        matched_temporal = True

    if base_date is None:
        match = _DATE_ISO.search(raw)
        if match:
            base_date = _safe_date(match.group(1), match.group(2), match.group(3))
            matched_temporal = matched_temporal or base_date is not None

    if base_date is None:
        match = _DATE_SLASH.search(raw)
        if match:
            first, second, year = match.groups()
            year = _normalise_year(year)
            # India commonly uses day-first dates. Flip only when the values
            # make the intended order unambiguous.
            if int(first) > 12 and int(second) <= 12:
                day, month = int(first), int(second)
            elif int(second) > 12 and int(first) <= 12:
                month, day = int(first), int(second)
            else:
                day, month = int(first), int(second)
            base_date = _safe_date(year, month, day)
            matched_temporal = matched_temporal or base_date is not None

    if base_date is None:
        match = _DATE_DMY.search(raw)
        if match:
            day, month_name, year = match.groups()
            month = _MONTHS.get(month_name.lower()[:3])
            if month:
                base_date = _safe_date(_normalise_year(year), month, day)
                matched_temporal = matched_temporal or base_date is not None

    if base_date is None:
        match = _DATE_MDY.search(raw)
        if match:
            month_name, day, year = match.groups()
            month = _MONTHS.get(month_name.lower()[:3])
            if month:
                base_date = _safe_date(_normalise_year(year), month, day)
                matched_temporal = matched_temporal or base_date is not None

    if base_date is None:
        match = _DATE_DM.search(raw)
        if match:
            day, month_name = match.groups()
            month = _MONTHS.get(month_name.lower()[:3])
            if month:
                base_date = _safe_date(now.year, month, day)
                matched_temporal = matched_temporal or base_date is not None

    if base_date is None:
        match = _DATE_MD.search(raw)
        if match:
            month_name, day = match.groups()
            month = _MONTHS.get(month_name.lower()[:3])
            if month:
                base_date = _safe_date(now.year, month, day)
                matched_temporal = matched_temporal or base_date is not None

    time_match = _TIME_RE.search(raw)
    if time_match:
        hour, minute, second, meridiem = time_match.groups()
        hour, minute = int(hour), int(minute)
        second = int(second or 0)
        if meridiem:
            if hour == 12:
                hour = 0
            if meridiem.lower() == "pm":
                hour += 12
        if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
            if base_date is None:
                base_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            base_date = base_date.replace(hour=hour, minute=minute, second=second)
            matched_temporal = True

    if base_date is None:
        return None if not matched_temporal else now.replace(microsecond=0)
    return base_date


def strip_temporal(text):
    """Remove date/time tokens so their digits cannot be read as amounts."""
    value = str(text or "")
    for pattern in (_DATE_ISO, _DATE_SLASH, _DATE_DMY, _DATE_MDY, _TIME_RE):
        value = pattern.sub(" ", value)
    value = re.sub(r"\b(today|yesterday|just now)\b", " ", value, flags=re.I)
    return value


# ---------------------------------------------------------------------------
# Amounts and balances
# ---------------------------------------------------------------------------

_NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_SIGNED_AMOUNT_RE = re.compile(
    rf"(?<![\w/])([+\-\u2212])\s*(?:\u20b9|rs\.?|inr)?\s*({_NUMBER})\b",
    re.I,
)
_BALANCE_RE = re.compile(
    rf"(?:updated\s+|closing\s+|available\s+|coin\s+|new\s+)?"
    rf"bal(?:ance)?\s*(?:is|after|:|-|=)?\s*"
    rf"(?:\u20b9|rs\.?|inr)?\s*({_NUMBER})",
    re.I,
)
_COIN_SUFFIX_RE = re.compile(rf"({_NUMBER})\s*(?:coins?|c)\b", re.I)
_COIN_PREFIX_RE = re.compile(
    rf"(?:coins?|amount)\s*(?:is|:|-|=)?\s*(?:\u20b9|rs\.?|inr)?\s*({_NUMBER})",
    re.I,
)
_PLAIN_NUMBER_RE = re.compile(rf"(?<![\w/])({_NUMBER})(?![\w/])")

_REFERENCE_RE = re.compile(
    r"\b(?:txn|trx|transaction|reference|ref)\s*"
    r"(?:id|no|number|#)?\s*[:#-]?\s*([A-Za-z0-9_-]{4,})\b",
    re.I,
)

_DATE_ONLY_HINT = re.compile(r"\b(?:19|20)\d{2}\b")


def _to_amount(value):
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    if number <= 0 or not number.is_integer():
        return None
    return int(number)


def extract_amount(text):
    """Return ``(amount, explicit_sign)`` for a transaction label."""
    value = strip_temporal(text)

    match = _SIGNED_AMOUNT_RE.search(value)
    if match:
        amount = _to_amount(match.group(2))
        if amount is not None:
            return amount, match.group(1)

    balance = _BALANCE_RE.search(value)
    if balance:
        amount = _to_amount(balance.group(1))
        if amount is not None:
            # A balance is not a transaction amount. Remove it and continue.
            value = value[: balance.start()] + " " + value[balance.end():]

    for pattern in (_COIN_SUFFIX_RE, _COIN_PREFIX_RE):
        match = pattern.search(value)
        if match:
            amount = _to_amount(match.group(1))
            if amount is not None:
                return amount, None

    # A bare number is only treated as an amount when the row clearly names a
    # coin movement, otherwise dates, IDs and balances would be misread.
    key = normalize_key(value)
    if any(
        marker in key
        for marker in (
            "coin", "credit", "debit", "bonus", "earned", "spent",
            "deduct", "request", "entry", "refund", "reward",
        )
    ):
        for match in _PLAIN_NUMBER_RE.finditer(value):
            token = match.group(1)
            if _DATE_ONLY_HINT.fullmatch(token):
                continue
            amount = _to_amount(token)
            if amount is not None:
                return amount, None

    return None, None


def extract_balance(text):
    """Return the updated/closing balance shown on a transaction row."""
    value = strip_temporal(text)
    match = _BALANCE_RE.search(value)
    if match:
        return _to_amount(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Direction and type
# ---------------------------------------------------------------------------

_CREDIT_WORDS = re.compile(
    r"\b(credit|credited|earned|added|received|reward|bonus|won|win|"
    r"refund|refunded|cashback|top\s*up|topup)\b",
    re.I,
)
_DEBIT_WORDS = re.compile(
    r"\b(debit|debited|deducted|deduction|spent|used|redeemed|charged|"
    r"request|entry|fee|purchase[d]?)\b",
    re.I,
)


def _build_type_lookup():
    lookup = []
    for canonical, aliases in CoinSettings.TRANSACTION_ALIASES.items():
        for alias in aliases:
            lookup.append((normalize_key(alias), canonical, alias))
    # Longest alias first so "referral registration bonus" wins over
    # "referral bonus".
    lookup.sort(key=lambda item: len(item[0]), reverse=True)
    return lookup


_TYPE_LOOKUP = _build_type_lookup()

# Aliases used for wording such as "Buy Coins" in a coin-purchase screen.
_PURCHASE_WORDS = re.compile(r"\b(coin purchase|buy coins|purchase coins|add coins|top up|top-up|recharge)\b", re.I)


def resolve_type(text):
    """Return ``(canonical_type, display_label)`` for a row label."""
    key = normalize_key(text)
    for alias_key, canonical, alias in _TYPE_LOOKUP:
        if not alias_key:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(alias_key)}(?![a-z0-9])", key):
            line = next(
                (
                    line
                    for line in _lines(text)
                    if alias_key in normalize_key(line)
                ),
                alias,
            )
            return canonical, normalize_spaces(line)

    # Unknown but well-formed rows still expose a description. Strip the
    # parts already consumed by the amount/date parser.
    cleaned = strip_temporal(text)
    cleaned = _SIGNED_AMOUNT_RE.sub(" ", cleaned)
    cleaned = _BALANCE_RE.sub(" ", cleaned)
    cleaned = _COIN_SUFFIX_RE.sub(" ", cleaned)
    cleaned = _COIN_PREFIX_RE.sub(" ", cleaned)
    cleaned = re.sub(
        r"\b(credit|credited|debit|debited|earned|added|deducted|spent|used)\b",
        " ",
        cleaned,
        flags=re.I,
    )
    for line in _lines(cleaned):
        candidate = normalize_spaces(line)
        if not candidate:
            continue
        if re.fullmatch(r"[\d\s,.:+\-]+", candidate):
            continue
        if len(candidate) > 80:
            continue
        return "unknown", candidate
    return None, None


def resolve_direction(text, sign=None, canonical_type=None):
    """Classify a row as ``credit`` or ``debit``."""
    key = normalize_key(text)

    # Explicit POS/ATM style indicators take priority over words in the type.
    if re.search(r"\b(credit|credited)\b", key):
        return "credit"
    if re.search(r"\b(debit|debited|deducted|deduction)\b", key):
        return "debit"

    # Prefer the configured mapping for a recognised transaction type.
    mapped = CoinSettings.TRANSACTION_DIRECTIONS.get(canonical_type or "")
    if mapped:
        return mapped

    if _PURCHASE_WORDS.search(key):
        return "credit"
    if _DEBIT_WORDS.search(key):
        return "debit"
    if _CREDIT_WORDS.search(key):
        return "credit"

    if sign in ("+",):
        return "credit"
    if sign in ("-", "\u2212"):
        return "debit"
    return None


# ---------------------------------------------------------------------------
# Transaction model
# ---------------------------------------------------------------------------

@dataclass
class CoinTransaction:
    type: str
    amount: int
    direction: str
    type_label: str = ""
    raw: str = ""
    occurred_at: Optional[datetime] = None
    balance_after: Optional[int] = None
    reference: Optional[str] = None
    index: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def is_credit(self):
        return self.direction == "credit"

    @property
    def is_debit(self):
        return self.direction == "debit"

    @property
    def signed_amount(self):
        return self.amount if self.is_credit else -self.amount

    @property
    def signature(self):
        return (
            self.type,
            self.amount,
            self.direction,
            self.occurred_at.isoformat() if self.occurred_at else "",
            self.balance_after,
        )

    def to_dict(self):
        return {
            "type": self.type,
            "type_label": self.type_label,
            "amount": self.amount,
            "direction": self.direction,
            "date_time": self.occurred_at.isoformat() if self.occurred_at else None,
            "balance_after": self.balance_after,
            "reference": self.reference,
            "raw": self.raw,
        }


def parse_transaction_text(text, type_directions=None):
    """Parse one visible transaction label into a :class:`CoinTransaction`.

    Returns ``None`` for headers, balance-only labels and unrelated UI text.
    ``type_directions`` can override the default direction map (used by unit
    tests and by a future configuration source).
    """
    raw = normalize_spaces(text)
    if not raw:
        return None

    amount, sign = extract_amount(text)
    if amount is None:
        return None

    canonical, label = resolve_type(text)
    direction = resolve_direction(text, sign=sign, canonical_type=canonical)
    if direction is None:
        return None

    # A row needs either a known transaction type or an explicit signed amount
    # / credit-debit marker. This prevents a random "50 coins" balance from
    # being recorded as a transaction.
    if canonical is None and sign is None and not re.search(
        r"\b(credit|credited|debit|debited|earned|added|deducted|spent|used)\b",
        raw,
        flags=re.I,
    ):
        return None

    if canonical is None:
        canonical = "unknown"

    reference_match = _REFERENCE_RE.search(raw)
    return CoinTransaction(
        type=canonical,
        amount=amount,
        direction=direction,
        type_label=label or canonical.replace("_", " ").title(),
        raw=raw,
        occurred_at=parse_datetime(raw),
        balance_after=extract_balance(raw),
        reference=reference_match.group(1) if reference_match else None,
    )


# ---------------------------------------------------------------------------
# History-wide assertions
# ---------------------------------------------------------------------------

def chronological_errors(transactions, newest_first=True):
    """Return a list of ordering errors (empty means the order is valid)."""
    stamped = [tx for tx in transactions if tx.occurred_at is not None]
    if len(stamped) < 2:
        return []

    errors = []
    pairs = zip(stamped, stamped[1:])
    for current, following in pairs:
        if newest_first and current.occurred_at < following.occurred_at:
            errors.append(
                f"{current.type_label or current.type} at {current.occurred_at} "
                f"appears before older {following.type_label or following.type} "
                f"at {following.occurred_at}"
            )
        if not newest_first and current.occurred_at > following.occurred_at:
            errors.append(
                f"{current.type_label or current.type} at {current.occurred_at} "
                f"appears after newer {following.type_label or following.type} "
                f"at {following.occurred_at}"
            )
    return errors


def balance_errors(transactions, displayed_balance=None, newest_first=True):
    """Validate the running balance shown on transaction rows.

    When the wallet shows ``Balance after: N`` on a row, walking from the
    newest row to the oldest must reproduce every older balance:

        balance_before = balance_after - signed_amount

    The opening balance must also be non-negative.
    """
    rows = list(transactions)
    if not newest_first:
        rows = list(reversed(rows))
    if not rows:
        return []

    errors = []
    running = displayed_balance
    if running is None:
        running = next(
            (tx.balance_after for tx in rows if tx.balance_after is not None),
            None,
        )
    if running is None:
        return []

    for tx in rows:
        if tx.balance_after is not None and tx.balance_after != running:
            errors.append(
                f"{tx.type_label or tx.type} shows balance {tx.balance_after} "
                f"but the running balance is {running}"
            )
        running -= tx.signed_amount

    if running < 0:
        errors.append(
            f"The history implies a negative opening coin balance ({running})"
        )
    return errors


def transaction_summary(transactions):
    credits = [tx for tx in transactions if tx.is_credit]
    debits = [tx for tx in transactions if tx.is_debit]
    return {
        "count": len(transactions),
        "credit_count": len(credits),
        "debit_count": len(debits),
        "credit_total": sum(tx.amount for tx in credits),
        "debit_total": sum(tx.amount for tx in debits),
        "net": sum(tx.signed_amount for tx in transactions),
    }


def find_transactions(transactions, transaction_type):
    """Return every transaction matching a canonical type (or display text)."""
    needle = normalize_key(transaction_type)
    matches = []
    for tx in transactions:
        candidates = {
            normalize_key(tx.type),
            normalize_key(tx.type_label),
            normalize_key(tx.type.replace("_", " ")),
        }
        if any(needle and needle in candidate for candidate in candidates):
            matches.append(tx)
    return matches


def duplicates(transactions):
    """Return transaction signatures that occur more than once consecutively."""
    seen = {}
    for tx in transactions:
        seen.setdefault(tx.signature, []).append(tx)
    return {signature: rows for signature, rows in seen.items() if len(rows) > 1}
