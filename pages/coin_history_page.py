"""Page object for the ABO Tribe coin wallet and Coin History screen."""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import CoinSettings
from pages.login_page import LoginPage
from utils import coin_parser
from utils.ui_locators import CoinLocators, LocationLocators


class CoinHistoryPage:
    """Reads, refreshes and validates the user's coin balance and history."""

    def __init__(self, driver, device=None):
        self.driver = driver
        self.device = device
        self.wait = WebDriverWait(driver, CoinSettings.TIMEOUT)
        self._transaction_cache = []

    # ------------------------------------------------------------- lifecycle
    def launch_app(self, wait_for_ui=True):
        self.driver.terminate_app(CoinSettings.APP_PACKAGE)
        self.driver.execute_script(
            "mobile: startActivity", {"component": CoinSettings.APP_COMPONENT}
        )
        time.sleep(3)
        self._dismiss_primer()
        if wait_for_ui:
            deadline = time.monotonic() + CoinSettings.OPEN_TIMEOUT
            while time.monotonic() < deadline:
                if self.is_login_screen():
                    return False
                if self.driver.find_elements(*LocationLocators.PRIMER_NOT_NOW):
                    self._dismiss_primer()
                if (
                    self.driver.find_elements(*CoinLocators.COINS_ENTRY)
                    or self.driver.find_elements(*CoinLocators.HISTORY_TITLE)
                    or self.driver.find_elements(*LoginPage.DASHBOARD)
                ):
                    return True
                time.sleep(0.5)
            return self.driver.current_package == CoinSettings.APP_PACKAGE
        return True

    def _dismiss_primer(self):
        buttons = self.driver.find_elements(*LocationLocators.PRIMER_NOT_NOW)
        if buttons:
            try:
                buttons[0].click()
                time.sleep(1)
            except (StaleElementReferenceException, WebDriverException):
                pass

    def is_login_screen(self):
        return bool(self.driver.find_elements(*LoginPage.MOBILE_NUMBER))

    def is_app_foreground(self):
        try:
            return self.driver.current_package == CoinSettings.APP_PACKAGE
        except WebDriverException:
            return False

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _label(element):
        try:
            content = (element.get_attribute("content-desc") or "").strip()
            text = (element.get_attribute("text") or "").strip()
        except (StaleElementReferenceException, WebDriverException):
            return ""
        values = []
        for value in (content, text):
            if value and value not in values:
                values.append(value)
        return "\n".join(values).strip()

    def _visible(self, locator):
        try:
            return bool(self.driver.find_elements(*locator))
        except WebDriverException:
            return False

    def _find_clickable(self, locator):
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except (StaleElementReferenceException, WebDriverException):
                continue
        return None

    def _click(self, locator, timeout=None):
        try:
            element = WebDriverWait(
                self.driver, timeout or CoinSettings.TIMEOUT
            ).until(EC.element_to_be_clickable(locator))
            element.click()
            time.sleep(1)
            return True
        except (TimeoutException, StaleElementReferenceException, WebDriverException):
            return False

    def page_text(self):
        try:
            return (self.driver.page_source or "").lower()
        except WebDriverException:
            return ""

    def _screen_size(self):
        try:
            size = self.driver.get_window_size()
            return int(size.get("width", 720)), int(size.get("height", 1280))
        except WebDriverException:
            return 720, 1280

    # ------------------------------------------------------------ navigation
    def go_home(self):
        if self.is_login_screen():
            return False
        for locator in (
            ("accessibility id", "Home"),
            ("xpath", "//android.widget.Button[@content-desc='Home']"),
        ):
            element = self._find_clickable(locator)
            if element is not None:
                try:
                    element.click()
                    time.sleep(2)
                    return True
                except (StaleElementReferenceException, WebDriverException):
                    pass
        return False

    def open_coins(self):
        """Open the coin/wallet screen from the authenticated app."""
        if self.is_login_screen():
            return False
        if self.is_history_loaded() or self.is_coins_screen():
            return True

        # Prefer the visible coin balance near the top of the screen.
        candidates = []
        for element in self.driver.find_elements(*CoinLocators.COINS_ENTRY):
            label = self._label(element)
            if not label or not re.search(r"\d", label):
                continue
            try:
                bounds = element.get_attribute("bounds") or ""
                match = re.match(r"\[\d+,(\d+)\]", bounds)
                top = int(match.group(1)) if match else 9999
            except (StaleElementReferenceException, WebDriverException):
                top = 9999
            candidates.append((top, element))

        for _, element in sorted(candidates, key=lambda item: item[0]):
            try:
                if element.is_displayed():
                    element.click()
                    time.sleep(2)
                    if self.is_coins_screen() or self.is_history_loaded():
                        return True
            except (StaleElementReferenceException, WebDriverException):
                continue

        # The coin pill is not always marked clickable. Tapping just left of
        # the profile/menu icon is the app's documented wallet entry point.
        width, _ = self._screen_size()
        for x_ratio in (0.68, 0.72, 0.62):
            self.driver.tap([(int(width * x_ratio), 107)])
            time.sleep(2)
            if self.is_coins_screen() or self.is_history_loaded():
                return True
        return False

    def is_coins_screen(self):
        source = self.page_text()
        return any(
            marker in source
            for marker in (
                "coin balance",
                "my coins",
                "available coins",
                "coin history",
                "buy coins",
                "coin purchase",
            )
        )

    def open_history(self):
        """Open Coin History, trying the wallet entry and both navigation paths."""
        if self.is_history_loaded():
            return True
        if self.is_login_screen():
            return False

        for attempt in range(3):
            if attempt == 0:
                opened = self.open_coins()
            else:
                opened = True

            if not opened:
                self.driver.back()
                time.sleep(1)
                if not self.is_coins_screen():
                    self.open_coins()

            history = self._find_clickable(CoinLocators.HISTORY_ENTRY)
            if history is not None:
                try:
                    history.click()
                    time.sleep(2)
                    if self.wait_for_history(timeout=8) in ("history", "empty"):
                        return True
                except (StaleElementReferenceException, WebDriverException):
                    pass

            # Some builds use a History tab inside the wallet, which is not
            # reported as clickable by UiAutomator. Tap the tab row instead.
            self._tap_history_tab_guess()
            if self.wait_for_history(timeout=6) in ("history", "empty"):
                return True

            if self.open_coins() and self.is_coins_screen():
                self._scroll(direction="down", percent=0.6)
                history = self._find_clickable(CoinLocators.HISTORY_ENTRY)
                if history is not None:
                    try:
                        history.click()
                        time.sleep(2)
                        if self.wait_for_history(timeout=8) in ("history", "empty"):
                            return True
                    except (StaleElementReferenceException, WebDriverException):
                        pass
        return self.wait_for_history(timeout=5) in ("history", "empty")

    def _tap_history_tab_guess(self):
        width, height = self._screen_size()
        # Common placements: wallet tabs near the top, or a "History" row
        # under the balance card.
        for x, y in (
            (width // 2, int(height * 0.20)),
            (int(width * 0.75), int(height * 0.20)),
            (width // 2, int(height * 0.30)),
        ):
            try:
                self.driver.tap([(x, y)])
                time.sleep(1)
                if self.is_history_loaded():
                    return True
            except WebDriverException:
                continue
        return False

    def wait_for_history(self, timeout=None):
        """Return 'history', 'empty', 'error' or 'timeout'."""
        timeout = timeout or CoinSettings.HISTORY_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.has_empty_state():
                return "empty"
            if self.has_error_state():
                return "error"
            if self.is_history_loaded():
                return "history"
            time.sleep(0.5)
        return "timeout"

    def is_history_loaded(self):
        if self.has_empty_state() or self.has_error_state():
            return True
        if self.driver.find_elements(*CoinLocators.HISTORY_TITLE):
            return True
        return bool(self.transactions(parse_only=True))

    def is_history_screen(self):
        return self.is_history_loaded() and not self.is_login_screen()

    def has_empty_state(self):
        if self._visible(CoinLocators.EMPTY_STATE):
            return True
        text = self.page_text()
        return any(marker in text for marker in CoinSettings.EMPTY_MARKERS)

    def has_error_state(self):
        if self._visible(CoinLocators.ERROR_STATE):
            return True
        text = self.page_text()
        return any(marker in text for marker in CoinSettings.ERROR_MARKERS)

    def has_retry(self):
        return self._visible(CoinLocators.RETRY)

    def retry(self):
        element = self._find_clickable(CoinLocators.RETRY)
        if element is None:
            return False
        try:
            element.click()
            time.sleep(2)
            return True
        except (StaleElementReferenceException, WebDriverException):
            return False

    def refresh(self):
        """Refresh the history via the refresh action, pull-to-refresh or relaunch."""
        if self.retry():
            return self.wait_for_history()
        for element in self.driver.find_elements(*CoinLocators.REFRESH):
            try:
                if element.is_displayed():
                    element.click()
                    time.sleep(2)
                    return self.wait_for_history()
            except (StaleElementReferenceException, WebDriverException):
                continue

        # Pull-to-refresh is the user-visible fallback when there is no button.
        try:
            self._scroll(direction="up", percent=0.9)
            time.sleep(2)
            if self.wait_for_history(timeout=6) in ("history", "empty"):
                return self.wait_for_history(timeout=6)
        except WebDriverException:
            pass

        self.launch_app()
        self.open_history()
        return self.wait_for_history()

    # --------------------------------------------------------------- balance
    def _header_balance(self):
        candidates = []
        for element in self.driver.find_elements(
            "xpath", "//*[@content-desc!='' or @text!='']"
        ):
            label = self._label(element)
            if not label:
                continue
            lowered = label.lower()
            if not any(marker in lowered for marker in CoinSettings.BALANCE_MARKERS):
                continue
            if any(
                alias in lowered
                for aliases in CoinSettings.TRANSACTION_ALIASES.values()
                for alias in aliases
            ):
                # Transaction rows also mention balance; prefer the header.
                continue
            amount = coin_parser.extract_balance(label)
            if amount is None:
                amount = coin_parser.extract_amount(label)[0]
            if amount is None:
                continue
            try:
                bounds = element.get_attribute("bounds") or ""
                match = re.match(r"\[\d+,(\d+)\]", bounds)
                top = int(match.group(1)) if match else 9999
            except (StaleElementReferenceException, WebDriverException):
                top = 9999
            candidates.append((top, amount))

        if candidates:
            return sorted(candidates, key=lambda item: item[0])[0][1]

        # A header such as "120 coins" does not contain the word balance.
        _, height = self._screen_size()
        header_candidates = []
        for element in self.driver.find_elements(
            "xpath", "//*[@content-desc!='' or @text!='']"
        ):
            label = self._label(element)
            amount = coin_parser.extract_amount(label)[0]
            if amount is None:
                continue
            try:
                bounds = element.get_attribute("bounds") or ""
                match = re.match(r"\[\d+,(\d+)\]", bounds)
                top = int(match.group(1)) if match else height
            except (StaleElementReferenceException, WebDriverException):
                top = height
            if top > height * 0.25:
                continue
            header_candidates.append((top, amount))
        if header_candidates:
            return sorted(header_candidates, key=lambda item: item[0])[0][1]
        return None

    def balance(self):
        """Return the wallet's current coin balance as an integer."""
        amount = self._header_balance()
        if amount is not None:
            return amount

        # The header scrolls out of the accessibility tree when the list is
        # scrolled to the bottom. Return to the top and retry before falling
        # back to a row's running balance.
        for _ in range(3):
            self._scroll(direction="up", percent=0.9)
            time.sleep(0.4)
            amount = self._header_balance()
            if amount is not None:
                return amount

        # Last resort: the balance shown on the newest transaction row in the
        # current (top) view.
        transactions = self._transactions_from_source()
        for transaction in transactions:
            if transaction.balance_after is not None:
                return transaction.balance_after
        return None

    # ---------------------------------------------------------- transactions
    @staticmethod
    def _node_label(node):
        content = (node.attrib.get("content-desc") or "").strip()
        text = (node.attrib.get("text") or "").strip()
        values = []
        for value in (content, text):
            if value and value not in values:
                values.append(value)
        return "\n".join(values).strip()

    def _page_root(self):
        try:
            return ET.fromstring(self.driver.page_source)
        except (ET.ParseError, WebDriverException):
            return None

    @staticmethod
    def _combined_label(node):
        labels = []
        for descendant in node.iter():
            label = CoinHistoryPage._node_label(descendant)
            if label and label not in labels:
                labels.append(label)
        return " | ".join(labels)

    @staticmethod
    def _too_many_amounts(label):
        """Reject an ancestor label that contains more than one transaction."""
        signed = re.findall(r"[+\-\u2212]\s*\d", label)
        with_coins = re.findall(r"\d[\d,.]*\s*coins?\b", label, flags=re.I)
        balances = len(re.findall(r"\bbal(?:ance)?\b", label, flags=re.I))
        dates = (
            len(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", label))
            + len(re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", label))
            + len(
                re.findall(
                    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)",
                    label,
                    flags=re.I,
                )
            )
        )
        if len(signed) + len(with_coins) > 2:
            return True
        if balances > 1 or dates > 1:
            return True

        key = coin_parser.normalize_key(label)
        transaction_types = set()
        for canonical, aliases in CoinSettings.TRANSACTION_ALIASES.items():
            for alias in aliases:
                alias_key = coin_parser.normalize_key(alias)
                if not alias_key:
                    continue
                occurrences = key.count(alias_key)
                if occurrences > 1:
                    return True
                if occurrences == 1:
                    transaction_types.add(canonical)
        return len(transaction_types) > 1

    def _transactions_from_source(self):
        root = self._page_root()
        if root is None:
            return []

        parent_map = {child: parent for parent in root.iter() for child in parent}
        candidates = []
        seen_row_roots = {}

        for index, node in enumerate(root.iter()):
            own = self._node_label(node)
            if not own:
                continue
            if len(own) > 800:
                continue

            best = None
            ancestor = node
            for _ in range(4):
                label = self._combined_label(ancestor)
                if label and len(label) <= 800 and not self._too_many_amounts(label):
                    transaction = coin_parser.parse_transaction_text(label)
                    if transaction is not None:
                        score = 0
                        if transaction.occurred_at is not None:
                            score += 2
                        if transaction.balance_after is not None:
                            score += 1
                        if transaction.type != "unknown":
                            score += 2
                        if transaction.direction in ("credit", "debit"):
                            score += 1
                        score += min(len(label) / 500.0, 1)
                        if best is None or score > best[0]:
                            best = (score, transaction, ancestor, label)
                ancestor = parent_map.get(ancestor)
                if ancestor is None:
                    break

            if best is None:
                continue

            _, transaction, row_root, label = best
            transaction.raw = coin_parser.normalize_spaces(label)
            transaction.index = index

            # The same row is reached from each child node. Deduplicate by
            # row root. If no row root groups the nodes, identical-looking
            # transactions are preserved unless their timestamps/reference
            # prove they are the same record.
            key = id(row_root)
            if key in seen_row_roots:
                existing = seen_row_roots[key]
                if transaction.occurred_at is None and transaction.reference is None:
                    # Keep the richer label for the same visual row.
                    if len(transaction.raw) > len(existing.raw):
                        seen_row_roots[key] = transaction
                continue
            seen_row_roots[key] = transaction
            candidates.append(transaction)

        candidates.sort(key=lambda tx: tx.index)

        # Final guard against child/sibling duplication when a row exposes a
        # timestamp or reference.
        unique = []
        seen_signatures = set()
        for transaction in candidates:
            if transaction.occurred_at or transaction.reference or transaction.balance_after:
                if transaction.signature in seen_signatures:
                    continue
                seen_signatures.add(transaction.signature)
            unique.append(transaction)
        self._transaction_cache = unique
        return unique

    def transactions(self, parse_only=False, max_scrolls=None):
        """Return visible transactions, optionally collecting the full list."""
        if parse_only:
            return self._transactions_from_source()
        return self.collect_all_transactions(max_scrolls=max_scrolls)

    def collect_all_transactions(self, max_scrolls=None):
        """Scroll the history list and merge unique transactions."""
        if not self.is_history_loaded() and not self.driver.find_elements(
            *CoinLocators.HISTORY_TITLE
        ):
            self.open_history()
        max_scrolls = max_scrolls if max_scrolls is not None else CoinSettings.MAX_SCROLLS

        collected = {}
        for _ in range(max_scrolls + 1):
            for transaction in self._transactions_from_source():
                # Rows without a timestamp/balance/reference are keyed by
                # type+amount+position so repeated identical credits remain
                # separate while the same row is not duplicated on scroll.
                key = (
                    transaction.signature
                    if (
                        transaction.occurred_at
                        or transaction.reference
                        or transaction.balance_after
                    )
                    else (
                        transaction.type,
                        transaction.amount,
                        transaction.direction,
                        transaction.index,
                        transaction.raw,
                    )
                )
                collected.setdefault(key, transaction)
            self._scroll(direction="down", percent=0.75)
            time.sleep(0.7)

        transactions = sorted(collected.values(), key=lambda tx: tx.index)
        self._transaction_cache = transactions
        return transactions

    def _scroll(self, direction="down", percent=0.75):
        try:
            self.driver.execute_script(
                "mobile: scrollGesture",
                {
                    "left": 24,
                    "top": 300,
                    "width": 672,
                    "height": 1000,
                    "direction": direction,
                    "percent": percent,
                },
            )
            return True
        except WebDriverException:
            return False

    def wait_for_transactions(self, timeout=None, max_scrolls=None):
        timeout = timeout or CoinSettings.HISTORY_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.has_empty_state() or self.has_error_state():
                return []
            transactions = self.collect_all_transactions(max_scrolls=max_scrolls)
            if transactions:
                return transactions
            time.sleep(1)
        return self.collect_all_transactions(max_scrolls=max_scrolls)

    def wait_for_transaction(self, transaction_type, timeout=None):
        timeout = timeout or CoinSettings.HISTORY_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            matches = coin_parser.find_transactions(
                self.transactions(), transaction_type
            )
            if matches:
                return matches
            if self.has_empty_state() or self.has_error_state():
                return []
            time.sleep(1)
        return []

    def find_transactions(self, transaction_type):
        return coin_parser.find_transactions(self.transactions(), transaction_type)

    def transaction_types(self):
        return {" ".join(tx.type.split("_")) for tx in self.transactions()}

    @property
    def summary(self):
        return coin_parser.transaction_summary(self.transactions())

    # --------------------------------------------------------------- checks
    def chronological_errors(self, transactions=None):
        return coin_parser.chronological_errors(
            transactions or self.transactions(),
            newest_first=CoinSettings.NEWEST_FIRST,
        )

    def balance_errors(self, transactions=None, displayed_balance=None):
        return coin_parser.balance_errors(
            transactions or self.transactions(),
            displayed_balance=(
                self.balance() if displayed_balance is None else displayed_balance
            ),
            newest_first=CoinSettings.NEWEST_FIRST,
        )

    def duplicate_transactions(self, transactions=None):
        return coin_parser.duplicates(transactions or self.transactions())

    def assert_chronological(self, transactions=None):
        errors = self.chronological_errors(transactions)
        assert not errors, "Coin History is not in chronological order: " + "; ".join(
            errors
        )

    def assert_balance_consistent(self, transactions=None, displayed_balance=None):
        errors = self.balance_errors(transactions, displayed_balance)
        assert not errors, "Coin balance is inconsistent with the history: " + "; ".join(
            errors
        )

    def assert_direction_indicators(self, transactions=None):
        transactions = transactions or self.transactions()
        assert transactions, "No transactions were available to validate"
        for transaction in transactions:
            assert transaction.direction in ("credit", "debit"), (
                f"Transaction has no credit/debit indicator: {transaction.raw!r}"
            )
            raw = transaction.raw.lower()
            has_indicator = any(
                marker in raw
                for marker in (
                    "+", "-", "\u2212", "credit", "debit", "earned", "added",
                    "deduct", "spent", "bonus", "request", "entry", "reward",
                )
            )
            assert has_indicator, (
                f"Transaction does not distinguish credit from debit: {transaction.raw!r}"
            )

    def has_user_switcher(self):
        return self._visible(CoinLocators.USER_SWITCHER)

    def contains_text(self, needle):
        return coin_parser.normalize_key(needle) in coin_parser.normalize_key(
            self.page_text()
        )

    # -------------------------------------------------------- purchase/error
    def is_purchase_page(self):
        return self._visible(CoinLocators.PURCHASE_TITLE) or any(
            marker in self.page_text() for marker in CoinSettings.PURCHASE_MARKERS
        )

    def open_purchase(self):
        if self.is_purchase_page():
            return True
        for locator in (
            CoinLocators.PURCHASE_TITLE,
            ("xpath", "//*[contains(translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'buy') or contains(translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'buy')]"),
        ):
            element = self._find_clickable(locator)
            if element is not None:
                try:
                    element.click()
                    time.sleep(2)
                    return self.is_purchase_page()
                except (StaleElementReferenceException, WebDriverException):
                    continue
        return False

    def has_insufficient_coins_message(self):
        if self._visible(CoinLocators.INSUFFICIENT_MESSAGE):
            return True
        text = self.page_text()
        return any(marker in text for marker in CoinSettings.INSUFFICIENT_MARKERS)

    def has_not_checked_in_message(self):
        if self._visible(CoinLocators.NOT_CHECKED_IN_MESSAGE):
            return True
        text = self.page_text()
        return any(marker in text for marker in CoinSettings.NOT_CHECKED_IN_MARKERS)

    def has_feature_unavailable_message(self):
        if self._visible(CoinLocators.FEATURE_UNAVAILABLE_MESSAGE):
            return True
        text = self.page_text()
        return any(marker in text for marker in CoinSettings.FEATURE_DISABLED_MARKERS)
