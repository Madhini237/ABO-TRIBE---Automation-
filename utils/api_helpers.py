"""Backend helpers for validating coin balances, history and reward records.

The mobile suite is authoritative for what the user sees, but several coin
requirements can only be proven against the backend:

* the wallet balance must match the stored balance;
* every credit/deduction must have a matching transaction record;
* signup/check-in/referral/profile rewards must not be created twice;
* ABO Settings must be the source of the configured amounts.

The client is deliberately generic (Frappe/ERPNext resource API by default)
and is controlled through environment variables so the suite can point at a
test site without code changes::

    ABO_API_BASE_URL=https://test.example.com
    ABO_API_TOKEN=api_key:api_secret
    # or
    ABO_API_KEY=...
    ABO_API_SECRET=...

When the API is not configured, backend-only tests skip with a clear message.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

from config.settings import CoinSettings


class BackendNotConfigured(RuntimeError):
    """Raised when a backend operation is attempted without configuration."""


class AboApiError(RuntimeError):
    def __init__(self, message, status=None, payload=None):
        super().__init__(message)
        self.status = status
        self.payload = payload


def _env_flag(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def _first_env(*names):
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


def _normalise_keys(value):
    if not isinstance(value, dict):
        return {}
    normalised = {}
    for key, item in value.items():
        normalised[str(key).strip().lower().replace(" ", "_").replace("-", "_")] = item
    return normalised


class AboBackendClient:
    """Small, read-mostly Frappe resource client for coin validation."""

    def __init__(
        self,
        base_url=None,
        token=None,
        api_key=None,
        api_secret=None,
        timeout=30,
        verify_tls=True,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token or ""
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.timeout = timeout
        self.verify_tls = verify_tls

    @classmethod
    def from_env(cls):
        return cls(
            base_url=_first_env("ABO_API_BASE_URL", "ABO_BASE_URL", "ERPNEXT_BASE_URL"),
            token=_first_env("ABO_API_TOKEN"),
            api_key=_first_env("ABO_API_KEY"),
            api_secret=_first_env("ABO_API_SECRET"),
            timeout=int(os.getenv("ABO_API_TIMEOUT", "30")),
            verify_tls=_env_flag("ABO_VERIFY_TLS", True),
        )

    # ------------------------------------------------------------- config
    @property
    def configured(self):
        return bool(self.base_url)

    @property
    def authenticated(self):
        return bool(self.token or (self.api_key and self.api_secret))

    def require_configured(self):
        if not self.configured:
            raise BackendNotConfigured(
                "Set ABO_API_BASE_URL (and ABO_API_TOKEN or ABO_API_KEY/"
                "ABO_API_SECRET) to enable backend coin validation."
            )

    def _headers(self):
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        elif self.api_key and self.api_secret:
            headers["Authorization"] = f"token {self.api_key}:{self.api_secret}"
        return headers

    # ------------------------------------------------------------- request
    def _request(self, path, method="GET", params=None, payload=None):
        self.require_configured()
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.base_url}/{path.lstrip('/')}"

        if params:
            query = urllib.parse.urlencode(
                {key: value for key, value in params.items() if value is not None},
                doseq=True,
            )
            if query:
                url = f"{url}{'&' if '?' in url else '?'}{query}"

        data = None
        headers = self._headers()
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            url, data=data, headers=headers, method=method.upper()
        )
        context = None
        if url.startswith("https://") and not self.verify_tls:
            context = ssl._create_unverified_context()

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout, context=context
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = body
            raise AboApiError(
                f"{method.upper()} {url} failed with HTTP {error.code}: {body[:500]}",
                status=error.code,
                payload=parsed,
            ) from error
        except urllib.error.URLError as error:
            raise AboApiError(f"{method.upper()} {url} failed: {error.reason}") from error

        if not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as error:
            raise AboApiError(f"{method.upper()} {url} returned invalid JSON") from error

        if isinstance(parsed, dict):
            if parsed.get("exc_type") or parsed.get("exception"):
                raise AboApiError(
                    f"Backend rejected {method.upper()} {url}: "
                    f"{parsed.get('exc_type') or parsed.get('exception')}",
                    payload=parsed,
                )
        return parsed

    @staticmethod
    def _records(payload):
        if payload is None:
            return []
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        if "data" in payload:
            data = payload["data"]
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                if isinstance(data.get("data"), list):
                    return data["data"]
                return [data]

        if "message" in payload:
            message = payload["message"]
            if isinstance(message, list):
                return [item for item in message if isinstance(item, dict)]
            if isinstance(message, dict):
                if isinstance(message.get("data"), list):
                    return message["data"]
                if isinstance(message.get("message"), list):
                    return message["message"]
                return [message]
            # A scalar message is a method result, not a document.
            return []

        if "result" in payload:
            result = payload["result"]
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return [result]

        if "name" in payload:
            return [payload]
        return []

    # ----------------------------------------------------------- resources
    def get_document(self, doctype, name):
        path = (
            f"/api/resource/{urllib.parse.quote(str(doctype), safe='')}/"
            f"{urllib.parse.quote(str(name), safe='')}"
        )
        records = self._records(self._request(path))
        if records:
            return records[0]
        # Some Frappe versions return the document at the top level rather
        # than inside "data"; _records handles that when "name" is present.
        return None

    def list_documents(
        self,
        doctype,
        filters=None,
        fields=None,
        limit=200,
        order_by=None,
    ):
        path = f"/api/resource/{urllib.parse.quote(str(doctype), safe='')}"
        page_size = min(max(int(limit), 1), 100)
        collected = []
        offset = 0

        while len(collected) < limit:
            params = {
                "limit_start": offset,
                "limit_page_length": min(page_size, limit - len(collected)),
            }
            if filters:
                params["filters"] = json.dumps(filters)
            if fields:
                params["fields"] = json.dumps(fields)
            if order_by:
                params["order_by"] = order_by

            page = self._records(self._request(path, params=params))
            if not page:
                break
            collected.extend(page)
            if len(page) < page_size:
                break
            offset += len(page)
            if offset > 10000:
                break
        return collected[:limit]

    def count_documents(self, doctype, filters=None):
        # Frappe supports limit_page_length=0 on many versions; this fallback
        # works everywhere and is enough for the small reward documents used
        # by the coin flows.
        return len(self.list_documents(doctype, filters=filters, limit=10000))

    # ------------------------------------------------------------ settings
    def get_abo_settings(self):
        doctype = os.getenv("ABO_SETTINGS_DOCTYPE", "ABO Settings")
        preferred_name = os.getenv("ABO_SETTINGS_NAME", "")
        if preferred_name:
            document = self.get_document(doctype, preferred_name)
            if document:
                return _normalise_keys(document)

        records = self.list_documents(doctype, limit=10)
        if records:
            return _normalise_keys(records[0])

        # Single DocTypes are sometimes not returned by the list endpoint.
        for name in (preferred_name, doctype, "ABO Settings"):
            if not name:
                continue
            try:
                document = self.get_document(doctype, name)
            except AboApiError:
                continue
            if document:
                return _normalise_keys(document)
        return {}

    def get_coin_settings(self):
        """Return ``{canonical_type: amount_or_None}`` from ABO Settings."""
        raw = self.get_abo_settings()
        amounts = {}
        for canonical, aliases in CoinSettings.SETTINGS_FIELDS.items():
            amount = None
            for alias in aliases:
                key = alias.strip().lower().replace(" ", "_").replace("-", "_")
                if key in raw:
                    amount = CoinSettings.normalize_amount(raw[key])
                    if amount is not None:
                        break
            amounts[canonical] = amount
        amounts["_raw"] = raw
        return amounts

    def get_configured_amount(self, transaction_type):
        amount = self.get_coin_settings().get(transaction_type)
        if amount is not None:
            return amount
        return CoinSettings.configured_amount(transaction_type)

    # ---------------------------------------------------------------- users
    def get_current_user(self):
        configured_user = os.getenv("ABO_USER", "").strip()
        if configured_user:
            return configured_user

        endpoint = os.getenv(
            "ABO_CURRENT_USER_ENDPOINT", "/api/method/frappe.auth.get_logged_user"
        )
        payload = self._request(endpoint)
        if isinstance(payload, dict):
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
            if isinstance(message, dict):
                for key in ("user", "email", "name"):
                    if message.get(key):
                        return str(message[key]).strip()
        return None

    def get_user_balance(self, user=None):
        """Return the stored wallet balance for a user, or None if not found."""
        user = user or self.get_current_user()
        balance_aliases = [
            field.strip()
            for field in os.getenv(
                "ABO_BALANCE_FIELDS",
                "coin_balance,coins,balance,total_coins,available_coins",
            ).split(",")
            if field.strip()
        ]

        endpoint = os.getenv("ABO_USER_BALANCE_ENDPOINT", "").strip()
        if endpoint:
            path = endpoint.format(user=urllib.parse.quote(str(user or ""), safe=""))
            payload = self._request(path, params={"user": user} if user else None)
            records = self._records(payload)
            candidates = records or ([payload] if isinstance(payload, dict) else [])
            for record in candidates:
                normalised = _normalise_keys(record)
                for alias in balance_aliases:
                    amount = CoinSettings.normalize_amount(normalised.get(alias))
                    if amount is not None:
                        return amount
            message = payload.get("message") if isinstance(payload, dict) else None
            if isinstance(message, (int, float, str)):
                return CoinSettings.normalize_amount(message)

        user_doctype = os.getenv("ABO_USER_DOCTYPE", "User")
        if user:
            try:
                document = self.get_document(user_doctype, user)
            except AboApiError:
                document = None
            if document:
                normalised = _normalise_keys(document)
                for alias in balance_aliases:
                    amount = CoinSettings.normalize_amount(normalised.get(alias))
                    if amount is not None:
                        return amount

        wallet_doctype = os.getenv("ABO_COIN_BALANCE_DOCTYPE", "Coin Balance")
        if user:
            filters = {os.getenv("ABO_COIN_USER_FIELD", "user"): user}
            try:
                wallets = self.list_documents(wallet_doctype, filters=filters, limit=5)
            except AboApiError:
                wallets = []
            for wallet in wallets:
                normalised = _normalise_keys(wallet)
                for alias in balance_aliases:
                    amount = CoinSettings.normalize_amount(normalised.get(alias))
                    if amount is not None:
                        return amount
        return None

    # -------------------------------------------------------------- history
    def get_coin_history(self, user=None, limit=None, successful_only=True):
        """Return normalised coin transactions, newest first."""
        user = user or self.get_current_user()
        limit = limit or int(os.getenv("ABO_COIN_HISTORY_LIMIT", "500"))

        endpoint = os.getenv("ABO_COIN_HISTORY_ENDPOINT", "").strip()
        if endpoint:
            path = endpoint.format(user=urllib.parse.quote(str(user or ""), safe=""))
            payload = self._request(
                path,
                params={"user": user, "limit": limit} if user else {"limit": limit},
            )
            records = self._records(payload)
            if not records and isinstance(payload, dict):
                message = payload.get("message")
                if isinstance(message, list):
                    records = message
        else:
            doctype = os.getenv("ABO_COIN_HISTORY_DOCTYPE", "Coin History")
            filters = {}
            if user:
                filters[os.getenv("ABO_COIN_USER_FIELD", "user")] = user
            records = self.list_documents(
                doctype,
                filters=filters or None,
                limit=limit,
                order_by=os.getenv("ABO_COIN_HISTORY_ORDER_BY", "creation desc"),
            )

        transactions = [
            self.normalize_transaction(record)
            for record in records
            if isinstance(record, dict)
        ]
        transactions = [tx for tx in transactions if tx is not None]
        if successful_only:
            transactions = [tx for tx in transactions if tx["successful"]]
        return transactions

    @staticmethod
    def normalize_transaction(record):
        if not isinstance(record, dict):
            return None
        normalised = _normalise_keys(record)

        status = str(
            normalised.get("status")
            or normalised.get("transaction_status")
            or normalised.get("state")
            or ""
        ).strip().lower()
        docstatus = normalised.get("docstatus")
        successful = status not in (
            "failed",
            "failure",
            "cancelled",
            "canceled",
            "error",
            "rejected",
            "declined",
            "pending",
        ) and str(docstatus) not in ("2",)

        amount = None
        negative_amount = False
        for alias in (
            "amount",
            "coins",
            "coin",
            "coin_amount",
            "value",
            "points",
        ):
            value = normalised.get(alias)
            if value is None or isinstance(value, bool):
                continue
            amount = CoinSettings.normalize_amount(value)
            if amount is not None:
                break
            # Backends commonly store deductions as negative amounts rather
            # than a separate direction field.
            try:
                number = float(str(value).replace(",", "").strip())
            except (TypeError, ValueError):
                continue
            if number < 0 and number.is_integer():
                amount = abs(int(number))
                negative_amount = True
                break
        if amount is None:
            return None

        raw_type = ""
        for alias in (
            "transaction_type",
            "type",
            "coin_type",
            "reason",
            "source",
            "reference_doctype",
        ):
            if normalised.get(alias):
                raw_type = str(normalised[alias])
                break

        from utils import coin_parser

        canonical, label = coin_parser.resolve_type(raw_type)
        if canonical is None:
            canonical = coin_parser.normalize_key(raw_type).replace(" ", "_") or "unknown"
        direction = None
        for alias in ("direction", "transaction_direction", "entry_type"):
            value = str(normalised.get(alias) or "").lower()
            if "credit" in value:
                direction = "credit"
                break
            if "debit" in value:
                direction = "debit"
                break
        if direction is None:
            direction = CoinSettings.TRANSACTION_DIRECTIONS.get(canonical)
        if direction is None:
            # A negative stored amount is an unambiguous deduction.
            direction = (
                "debit"
                if negative_amount
                or str(normalised.get("amount", "")).strip().startswith("-")
                else "credit"
            )

        occurred_at = None
        for alias in (
            "transaction_date",
            "date",
            "timestamp",
            "creation",
            "modified",
            "time",
        ):
            value = normalised.get(alias)
            if value:
                occurred_at = coin_parser.parse_datetime(str(value))
                if occurred_at is not None:
                    break

        reference = None
        for alias in (
            "reference",
            "reference_name",
            "transaction_id",
            "txn_id",
            "name",
        ):
            if normalised.get(alias):
                reference = str(normalised[alias])
                break

        return {
            "type": canonical,
            "type_label": label or raw_type,
            "amount": amount,
            "direction": direction,
            "signed_amount": amount if direction == "credit" else -amount,
            "occurred_at": occurred_at,
            "reference": reference,
            "successful": successful,
            "raw": record,
        }

    # ------------------------------------------------------------- rewards
    @staticmethod
    def reward_doctype(kind):
        override = os.getenv(f"ABO_DOCTYPE_{kind.upper()}")
        if override:
            return override
        return CoinSettings.BACKEND_DOCTYPES.get(kind, kind)

    def get_reward_documents(self, kind, user=None):
        user = user or self.get_current_user()
        doctype = self.reward_doctype(kind)
        filters = {}
        if user:
            filters[os.getenv("ABO_COIN_USER_FIELD", "user")] = user
        return self.list_documents(
            doctype,
            filters=filters or None,
            limit=int(os.getenv("ABO_REWARD_DOC_LIMIT", "200")),
            order_by="creation asc",
        )

    def assert_no_duplicate_rewards(self, kind, user=None, reference_field=None):
        """Return reward documents and raise when a single-use reward repeats.

        Signup, check-in and profile completion are single-use rewards. Referral
        rewards are repeatable but must be unique per referred user; pass a
        ``reference_field`` (for example ``referred_user``) to enforce that.
        """
        documents = self.get_reward_documents(kind, user=user)
        single_use = kind in (
            "signup_bonus",
            "checkin_bonus",
            "profile_completion_bonus",
        )
        if single_use and len(documents) > 1:
            raise AssertionError(
                f"{kind} was awarded {len(documents)} times for {user}: "
                f"{[doc.get('name') for doc in documents]}"
            )
        if reference_field:
            seen = {}
            for document in documents:
                value = document.get(reference_field)
                if not value:
                    continue
                seen.setdefault(str(value), []).append(document.get("name"))
            duplicates = {key: value for key, value in seen.items() if len(value) > 1}
            if duplicates:
                raise AssertionError(
                    f"{kind} has duplicate rewards for {reference_field}: {duplicates}"
                )
        return documents

    def find_duplicate_transactions(self, transactions=None):
        transactions = transactions or self.get_coin_history()
        seen = {}
        for transaction in transactions:
            key = (
                transaction["type"],
                transaction["amount"],
                transaction["direction"],
                transaction["occurred_at"].isoformat()
                if transaction["occurred_at"]
                else "",
                transaction["reference"] or "",
            )
            seen.setdefault(key, []).append(transaction)
        return {key: rows for key, rows in seen.items() if len(rows) > 1}
