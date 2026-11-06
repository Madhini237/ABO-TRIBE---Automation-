"""Coin History, coin credit and coin deduction flows.

Coverage map
------------
Flow 1     Coin History display, balance, refresh, empty/error and privacy
Flow 2.1   Signup bonus
Flow 2.2   Check-in bonus (auto/manual approval and pending/rejected)
Flow 2.3   Referral registration bonus
Flow 2.4   Referral bonus for a successful referral
Flow 2.5   Profile completion bonus
Flow 2.6   Game win bonus
Flow 2.7   Multiple credits
Flow 3.1   Skip the Queue deduction
Flow 3.2   Song Request deduction
Flow 3.3   Shoutout Request deduction
Flow 3.4   Game entry deduction
Flow 3.5   Multiple deductions and duplicate safety
Flow 4     Insufficient coins
Flow 5     User not checked in
Flow 6     Feature disabled
Flow 7     Invalid referral / ineligible referral
Flow 8     Profile completion without check-in
Flow 9     Transaction integrity and retry safety
Flow 10    ABO Settings coin configuration

Tests that need a live backend skip when ``ABO_API_BASE_URL`` is not set.
Tests that need a new user prompt for a fresh mobile number (or use
``COIN_SIGNUP_MOBILE``/``SIGNUP_MOBILE_NUMBER`` when configured) and capture
the OTP from the device SMS notification, the same way the login/signup suite
does.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from contextlib import contextmanager

import pytest

from config.settings import CoinSettings
from pages.signup_page import SignupPage
from utils import coin_parser
from utils.auth_flow import (
    login_with_captured_otp,
    prompt_mobile_number,
    request_otp_and_capture,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FEATURE_LABELS = {
    "skip_the_queue": "Skip the Queue",
    "song_request": "Song Request",
    "shoutout_request": "Shoutout Request",
    "game_entry": "Game Entry",
}


def _launch_history(page):
    """Launch the app and open Coin History; skip when it is unreachable."""
    if not page.launch_app():
        if page.is_login_screen():
            pytest.skip("ABO Tribe is signed out; sign in before running coin tests")
        raise AssertionError("The ABO Tribe app did not open")
    if not page.open_history():
        pytest.skip("Coin History is not reachable in the current app build")
    status = page.wait_for_history()
    assert status in ("history", "empty"), (
        f"Coin History did not settle on a transaction or empty state ({status})"
    )
    return status


def _settings_amount(backend, transaction_type):
    try:
        amount = backend.get_configured_amount(transaction_type)
    except Exception:
        amount = None
    if amount is not None:
        return amount
    return CoinSettings.configured_amount(transaction_type)


def _backend_user(backend):
    try:
        return backend.get_current_user()
    except Exception:
        return None


def _tx_key(transaction):
    return (
        transaction.type,
        transaction.amount,
        transaction.direction,
        transaction.occurred_at.date().isoformat() if transaction.occurred_at else "",
        transaction.balance_after,
    )


def _new_transactions(before, after):
    before_keys = {_tx_key(transaction) for transaction in before}
    return [transaction for transaction in after if _tx_key(transaction) not in before_keys]


def _login(driver, mobile_number):
    login = login_with_captured_otp(driver, mobile_number)
    assert login.is_dashboard_displayed(), "Could not sign in with the configured test user"


@contextmanager
def _preserve_session(driver):
    """Restore the suite's signed-in user after a flow that registers a user."""
    mobile = os.getenv("TEST_MOBILE_NUMBER", "").strip()
    try:
        yield
    finally:
        if mobile:
            try:
                _login(driver, mobile)
            except Exception as error:  # best effort; never hide the real result
                print(f"WARNING: could not restore the original login session: {error}")


def _profile_data():
    raw = os.getenv("SIGNUP_PROFILE_DATA", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _signup_mobile():
    """Return the configured new-user number, or ask for one at runtime."""
    configured = CoinSettings.SIGNUP_MOBILE or os.getenv("SIGNUP_MOBILE_NUMBER", "")
    if configured:
        digits = "".join(character for character in configured if character.isdigit())
        assert len(digits) >= 10, (
            "COIN_SIGNUP_MOBILE must contain a 10-digit mobile number"
        )
        return digits[-10:]

    return prompt_mobile_number(
        "Enter a new 10-digit mobile number for the coin signup flow: ",
        validator=SignupPage.ensure_new_mobile_number,
    )


def _register_new_user(
    driver,
    referral_code=None,
    require_referral=False,
    mobile=None,
):
    mobile = mobile or _signup_mobile()

    signup = SignupPage(driver)
    signup.prepare_login_screen()
    referral_applied = False

    def apply_referral():
        nonlocal referral_applied
        if referral_code:
            referral_applied = signup.apply_referral_code(referral_code)

    otp = request_otp_and_capture(
        driver,
        signup,
        mobile,
        before_request=apply_referral,
    )
    signup.enter_otp(otp)
    stage = signup.wait_for_registration_stage()

    if stage == "profile":
        if referral_code and not referral_applied:
            referral_applied = signup.apply_referral_code(referral_code)
        if require_referral and not referral_applied:
            pytest.skip("This build does not expose a referral-code field during signup")
        profile = _profile_data()
        if profile:
            signup.fill_profile_details(profile)
            signup.submit_profile_details()
    elif stage == "bonus":
        if require_referral and not referral_applied:
            pytest.skip("This build does not expose a referral-code field during signup")
        signup.handle_signup_bonus_dialog()

    if require_referral and not referral_applied:
        pytest.skip("The referral code could not be entered before registration")

    signup.wait_for_dashboard()
    return mobile, referral_applied


def _open_history_after_action(page):
    """Return to Coin History after acting on a bar/game screen."""
    page.launch_app()
    if not page.open_history():
        pytest.skip("Coin History became unreachable after the action")
    status = page.wait_for_history()
    assert status in ("history", "empty"), f"Coin History did not reload ({status})"
    return status


def _assert_ui_matches_backend(page, backend, transactions=None):
    transactions = transactions or page.transactions()
    backend_transactions = backend.get_coin_history()
    assert backend_transactions, "The backend returned no coin transactions to compare"

    # The UI may hide the running balance, so compare on type, amount,
    # direction and date. Dates are compared at day granularity because the
    # history shows the local date while the backend stores a timestamp.
    backend_counts = Counter(
        (
            item.get("type"),
            item.get("amount"),
            item.get("direction"),
            item.get("occurred_at").date().isoformat()
            if item.get("occurred_at")
            else "",
        )
        for item in backend_transactions
    )
    missing = []
    for transaction in transactions:
        backend_key = (
            transaction.type,
            transaction.amount,
            transaction.direction,
            transaction.occurred_at.date().isoformat()
            if transaction.occurred_at
            else "",
        )
        if backend_counts[backend_key] <= 0:
            missing.append(transaction)
        else:
            backend_counts[backend_key] -= 1
    assert not missing, (
        "Coin History contains transactions that are not present in the backend "
        f"for the current user: {[tx.to_dict() for tx in missing]}"
    )


def _trigger_deduction(coin_actions, kind, bar_name=None):
    if kind == "skip_the_queue":
        return coin_actions.trigger_skip_the_queue(bar_name=bar_name)
    if kind == "song_request":
        return coin_actions.submit_song_request(bar_name=bar_name)
    if kind == "shoutout_request":
        return coin_actions.send_shoutout(bar_name=bar_name)
    if kind == "game_entry":
        return coin_actions.start_game(bar_name=bar_name)
    raise ValueError(kind)


def _assert_deduction(page, backend, kind, result):
    """Assert one successful coin deduction and its matching backend record."""
    if not result.attempted:
        pytest.skip(f"{FEATURE_LABELS.get(kind, kind)} is not reachable: {result.message}")

    status = _open_history_after_action(page)
    transactions = page.transactions() if status == "history" else []
    matches = coin_parser.find_transactions(transactions, kind)
    if result.status in ("insufficient_coins", "not_checked_in", "feature_unavailable"):
        pytest.skip(
            f"{FEATURE_LABELS.get(kind, kind)} was blocked by {result.status}: "
            f"{result.message}"
        )
    assert matches, (
        f"No {FEATURE_LABELS.get(kind, kind)} deduction appeared in Coin History; "
        f"action result={result.status}, message={result.message!r}"
    )

    transaction = matches[0]
    assert transaction.is_debit, (
        f"{FEATURE_LABELS.get(kind, kind)} must be a deduction, got "
        f"{transaction.direction}: {transaction.raw!r}"
    )
    expected = _settings_amount(backend, kind)
    if expected is not None:
        assert transaction.amount == expected, (
            f"{FEATURE_LABELS.get(kind, kind)} deducted {transaction.amount} coins, "
            f"but ABO Settings configures {expected}"
        )

    user = _backend_user(backend)
    documents = backend.get_reward_documents(kind, user=user)
    assert documents, (
        f"No backend record was created in "
        f"{CoinSettings.BACKEND_DOCTYPES.get(kind, kind)} for {kind}"
    )
    return transaction


def _checked_in_or_skip(coin_actions):
    result = coin_actions.check_in()
    if not result.attempted:
        pytest.skip(f"Could not reach the check-in flow: {result.message}")
    if result.status in ("pending", "rejected"):
        pytest.skip(
            f"Check-in is {result.status}; coin features require an accepted check-in"
        )
    assert result.status in ("accepted", "already_checked_in"), (
        f"Check-in did not complete: {result.status} ({result.message})"
    )
    return result


# ---------------------------------------------------------------------------
# Flow 1 - General Coin History
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.positive
@pytest.mark.smoke
def test_flow_01_coin_history_displays_transactions_and_balance(
    coin_history_page, backend
):
    status = _launch_history(coin_history_page)
    balance = coin_history_page.balance()
    assert balance is not None, "The coin balance was not visible on Coin History"
    assert balance >= 0, f"The displayed coin balance is negative: {balance}"

    if status == "empty":
        assert coin_history_page.has_empty_state(), "Empty history has no empty-state message"
        backend_balance = backend.get_user_balance()
        if backend_balance is not None:
            assert balance == backend_balance, (
                f"The empty history shows {balance} coins but the backend stores "
                f"{backend_balance}"
            )
        return

    transactions = coin_history_page.wait_for_transactions()
    assert transactions, "Coin History displayed neither transactions nor an empty state"

    for transaction in transactions:
        assert transaction.type, f"Transaction has no type: {transaction.raw!r}"
        assert transaction.amount > 0, f"Transaction has no positive amount: {transaction.raw!r}"
        assert transaction.direction in ("credit", "debit"), (
            f"Transaction direction is missing: {transaction.raw!r}"
        )
        if not CoinSettings.ALLOW_MISSING_TIMESTAMPS:
            assert transaction.occurred_at is not None, (
                f"Transaction has no visible date/time: {transaction.raw!r}"
            )

    coin_history_page.assert_chronological(transactions)
    coin_history_page.assert_direction_indicators(transactions)
    coin_history_page.assert_balance_consistent(transactions, balance)

    backend_balance = backend.get_user_balance()
    if backend_balance is not None:
        assert balance == backend_balance, (
            f"Coin History shows {balance} coins but the backend stores "
            f"{backend_balance}"
        )

    _assert_ui_matches_backend(coin_history_page, backend, transactions)


@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.positive
def test_flow_01_refresh_keeps_history_and_balance_consistent(coin_history_page):
    status = _launch_history(coin_history_page)
    before = coin_history_page.transactions()
    before_balance = coin_history_page.balance()

    for _ in range(2):
        new_status = coin_history_page.refresh()
        assert new_status in ("history", "empty"), f"Refresh failed ({new_status})"
        after = coin_history_page.transactions()
        assert [_tx_key(tx) for tx in after] == [_tx_key(tx) for tx in before], (
            "Refreshing Coin History changed the transactions"
        )
        assert coin_history_page.balance() == before_balance, (
            "Refreshing Coin History changed the displayed balance"
        )

    if status == "history":
        assert before, "The history was reported as loaded but contained no rows"


@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.negative
def test_flow_01_empty_history_message(coin_history_page):
    status = _launch_history(coin_history_page)
    if status != "empty":
        pytest.skip("The current test user has transactions; empty state cannot be forced")

    assert coin_history_page.has_empty_state(), "No empty-state message was displayed"
    assert coin_history_page.balance() is not None, "The empty history has no coin balance"
    assert not coin_history_page.transactions(parse_only=True), (
        "The empty state still rendered transaction rows"
    )


@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.negative
def test_flow_01_history_api_failure_is_handled(
    coin_history_page, device, preserve_device_state
):
    _launch_history(coin_history_page)
    if not device.set_http_proxy(CoinSettings.API_FAILURE_PROXY):
        pytest.skip(
            "This device denies WRITE_SECURE_SETTINGS, so the API-failure proxy "
            "cannot be configured"
        )
    try:
        coin_history_page.launch_app()
        coin_history_page.open_history()
        status = coin_history_page.wait_for_history(timeout=12)
        assert (
            status == "error"
            or coin_history_page.has_error_state()
            or coin_history_page.has_retry()
        ), "A Coin History API failure was not surfaced to the user"
    finally:
        device.clear_http_proxy()

    coin_history_page.launch_app()
    assert coin_history_page.open_history(), "Coin History did not recover after the API returned"
    assert coin_history_page.wait_for_history() in ("history", "empty"), (
        "Coin History did not recover after the API failure was removed"
    )


@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.negative
def test_flow_01_users_cannot_open_another_users_history(
    coin_history_page, backend
):
    other = CoinSettings.OTHER_USER_MOBILE.strip()
    if not other:
        pytest.skip("Set COIN_OTHER_USER_MOBILE to exercise cross-user history access")

    _launch_history(coin_history_page)
    assert not coin_history_page.has_user_switcher(), (
        "Coin History exposes a user/account switcher, which could reveal another "
        "user's transactions"
    )
    assert not coin_history_page.contains_text(other), (
        f"Another user's phone number ({other}) is visible on Coin History"
    )

    current_user = _backend_user(backend)
    assert current_user and other not in str(current_user), (
        "The app session is not the current user; cross-user scoping cannot be verified"
    )
    transactions = coin_history_page.transactions()
    if transactions:
        _assert_ui_matches_backend(coin_history_page, backend, transactions)


# ---------------------------------------------------------------------------
# Flow 2 - Credits
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.signup
@pytest.mark.positive
def test_flow_02_01_signup_bonus_credited_once(driver, coin_history_page, backend):
    with _preserve_session(driver):
        mobile, _ = _register_new_user(driver)
        status = _launch_history(coin_history_page)
        assert status != "empty", "The Signup Bonus transaction is missing for a new user"

        transactions = coin_history_page.wait_for_transaction("signup_bonus")
        assert transactions, "Signup Bonus was not recorded in Coin History"
        expected = _settings_amount(backend, "signup_bonus")
        if expected is not None:
            assert all(tx.amount == expected for tx in transactions), (
                f"Signup Bonus is {[tx.amount for tx in transactions]}, expected {expected}"
            )
        assert all(tx.is_credit for tx in transactions)

        user = _backend_user(backend) or mobile
        documents = backend.get_reward_documents("signup_bonus", user=user)
        assert len(documents) == 1, (
            f"Expected exactly one signup_bonus_coin document, got {len(documents)}"
        )

        before = [tx for tx in coin_history_page.transactions() if tx.type == "signup_bonus"]
        coin_history_page.refresh()
        after = [
            tx for tx in coin_history_page.transactions() if tx.type == "signup_bonus"
        ]
        assert len(after) == len(before), "Refreshing created a duplicate Signup Bonus"


@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.positive
def test_flow_02_02_checkin_bonus_after_acceptance(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    before = coin_history_page.transactions()
    user = _backend_user(backend)
    documents_before = (
        len(backend.get_reward_documents("checkin_bonus", user=user)) if user else None
    )

    result = coin_actions.check_in()
    if not result.attempted:
        pytest.skip(f"Could not reach the check-in flow: {result.message}")
    if result.status in ("pending", "rejected"):
        after = coin_history_page.transactions()
        new_bonus = [
            tx
            for tx in _new_transactions(before, after)
            if tx.type == "checkin_bonus"
        ]
        assert not new_bonus, (
            f"Check-in Bonus was credited while the check-in was {result.status}"
        )
        pytest.skip(
            f"Check-in is {result.status}; an accepted check-in is required for the "
            "positive bonus assertion"
        )

    assert result.status in ("accepted", "already_checked_in"), (
        f"Check-in did not complete: {result.status} ({result.message})"
    )

    _open_history_after_action(coin_history_page)
    transactions = coin_history_page.wait_for_transaction("checkin_bonus")
    assert transactions, "Check-in Bonus was not recorded after an accepted check-in"
    expected = _settings_amount(backend, "checkin_bonus")
    if expected is not None:
        assert transactions[0].amount == expected
    assert transactions[0].is_credit

    documents = backend.get_reward_documents("checkin_bonus", user=user)
    if result.status == "accepted" and documents_before is not None:
        assert len(documents) == documents_before + 1, (
            "An accepted check-in did not create exactly one new "
            f"checkin_bonus_coin document (before={documents_before}, "
            f"after={len(documents)})"
        )
    else:
        assert documents, "No checkin_bonus_coin document exists for the checked-in user"


@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.negative
def test_flow_02_02_no_checkin_bonus_while_pending_or_rejected(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    before = coin_history_page.transactions()

    result = coin_actions.check_in()
    if not result.attempted:
        pytest.skip(f"Could not reach the check-in flow: {result.message}")
    if result.status not in ("pending", "rejected"):
        pytest.skip("This bar auto-approves check-ins; pending/rejected state cannot be forced")

    _open_history_after_action(coin_history_page)
    after = coin_history_page.transactions()
    new_bonus = [
        tx for tx in _new_transactions(before, after) if tx.type == "checkin_bonus"
    ]
    assert not new_bonus, (
        f"Coins were credited while check-in was {result.status}: {new_bonus}"
    )

    user = _backend_user(backend)
    assert not backend.get_reward_documents("checkin_bonus", user=user), (
        "A checkin_bonus_coin document exists for a pending/rejected check-in"
    )


@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.signup
@pytest.mark.positive
def test_flow_02_03_referral_registration_bonus(driver, coin_history_page, backend):
    if not CoinSettings.REFERRAL_CODE:
        pytest.skip("Set COIN_REFERRAL_CODE with a valid referral code")

    with _preserve_session(driver):
        mobile, applied = _register_new_user(
            driver,
            referral_code=CoinSettings.REFERRAL_CODE,
            require_referral=True,
        )
        assert applied
        status = _launch_history(coin_history_page)
        assert status != "empty", "Referral Registration Bonus was not recorded"

        transactions = coin_history_page.wait_for_transaction(
            "referral_registration_bonus"
        )
        assert transactions, "Referral Registration Bonus is missing from Coin History"
        expected = _settings_amount(backend, "referral_registration_bonus")
        if expected is not None:
            assert transactions[0].amount == expected
        assert transactions[0].is_credit

        user = _backend_user(backend) or mobile
        documents = backend.get_reward_documents(
            "referral_registration_bonus", user=user
        )
        if not documents:
            # The backend may store both referral rewards in the same doctype.
            documents = backend.get_reward_documents("referral_bonus", user=user)
        assert documents, "No referral_bonus_coin document was created"


@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.positive
def test_flow_02_04_referral_bonus_for_referrer(driver, coin_history_page, backend):
    if not CoinSettings.REFERRER_MOBILE:
        pytest.skip("Set COIN_REFERRER_MOBILE to verify referral rewards")

    with _preserve_session(driver):
        _login(driver, CoinSettings.REFERRER_MOBILE)
        _launch_history(coin_history_page)
        transactions = coin_history_page.find_transactions("referral_bonus")
        if not transactions:
            pytest.skip(
                "The configured referrer has no successful referral reward yet; "
                "register a referred user before running this flow"
            )

        expected = _settings_amount(backend, "referral_bonus")
        if expected is not None:
            assert all(tx.amount == expected for tx in transactions)
        assert all(tx.is_credit for tx in transactions)

        user = _backend_user(backend)
        documents = backend.get_reward_documents("referral_bonus", user=user)
        assert documents, "No referral_bonus_coin document exists for the referrer"
        reference_field = os.getenv("ABO_REFERRAL_REFERENCE_FIELD", "referred_user")
        backend.assert_no_duplicate_rewards(
            "referral_bonus", user=user, reference_field=reference_field
        )

        registration = coin_history_page.find_transactions(
            "referral_registration_bonus"
        )
        if registration:
            assert all(tx.type == "referral_registration_bonus" for tx in registration), (
                "Referral registration and referral reward transactions are mixed"
            )


@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.positive
def test_flow_02_05_profile_completion_bonus(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)

    before = coin_history_page.transactions()
    result = coin_actions.complete_profile()
    if not result.attempted:
        pytest.skip(f"Profile completion is not reachable: {result.message}")
    if result.status == "feature_unavailable":
        pytest.skip("Profile editing is unavailable in this build")

    _open_history_after_action(coin_history_page)
    transactions = coin_history_page.wait_for_transaction(
        "profile_completion_bonus"
    )
    if not transactions and result.status == "success":
        pytest.fail("Profile was saved but Profile Completion Bonus was not credited")
    if not transactions:
        pytest.skip("The profile was already complete; no new reward was expected")

    expected = _settings_amount(backend, "profile_completion_bonus")
    if expected is not None:
        assert transactions[0].amount == expected
    assert transactions[0].is_credit

    user = _backend_user(backend)
    documents = backend.get_reward_documents(
        "profile_completion_bonus", user=user
    )
    assert len(documents) == 1, (
        "Profile Completion Bonus must have exactly one backend record; "
        f"found {len(documents)}"
    )


@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.positive
def test_flow_02_06_game_win_bonus(coin_actions, coin_history_page, backend):
    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)

    result = coin_actions.play_until_win()
    if not result.attempted:
        pytest.skip(f"Game flow is not reachable: {result.message}")
    if result.blocked:
        pytest.skip(f"Game flow was blocked by {result.status}: {result.message}")
    if result.status != "won":
        pytest.skip("No game win occurred in the configured number of attempts")

    _open_history_after_action(coin_history_page)
    wins = coin_history_page.wait_for_transaction("game_win_bonus")
    assert wins, "A game win did not create a Game Win Bonus transaction"
    expected = _settings_amount(backend, "game_win_bonus")
    if expected is not None:
        assert wins[0].amount == expected, (
            f"Game Win Bonus credited {wins[0].amount} coins, expected {expected}"
        )
    assert wins[0].is_credit

    entries = coin_history_page.find_transactions("game_entry")
    assert entries, "Game entry deduction was not recorded separately from the win bonus"
    assert entries[0].is_debit, "Game entry was recorded as a credit"
    assert wins[0].direction != entries[0].direction, (
        "Game entry and Game Win Bonus are not distinguished in Coin History"
    )


@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.positive
def test_flow_02_07_multiple_credits_are_separate(coin_history_page):
    _launch_history(coin_history_page)
    transactions = coin_history_page.transactions()
    credits = [tx for tx in transactions if tx.is_credit]
    if len(credits) < 2:
        pytest.skip("The current user has fewer than two credit transactions")

    assert len({_tx_key(tx) for tx in credits}) == len(credits), (
        "Two credit rewards were merged into one transaction"
    )
    assert all(tx.amount > 0 for tx in credits)
    assert sum(tx.amount for tx in credits) == coin_history_page.summary["credit_total"], (
        "The credit total does not equal the sum of the individual credits"
    )
    coin_history_page.assert_balance_consistent(transactions)


# ---------------------------------------------------------------------------
# Flow 3 - Deductions
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.positive
def test_flow_03_01_skip_the_queue_deduction(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)
    result = coin_actions.trigger_skip_the_queue()
    _assert_deduction(coin_history_page, backend, "skip_the_queue", result)


@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.positive
def test_flow_03_02_song_request_deduction(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)
    result = coin_actions.submit_song_request()
    _assert_deduction(coin_history_page, backend, "song_request", result)


@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.positive
def test_flow_03_03_shoutout_request_deduction(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)
    result = coin_actions.send_shoutout()
    _assert_deduction(coin_history_page, backend, "shoutout_request", result)


@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.positive
def test_flow_03_04_game_entry_deduction(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)
    result = coin_actions.start_game()
    _assert_deduction(coin_history_page, backend, "game_entry", result)


@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.positive
def test_flow_03_05_multiple_deductions_are_separate(coin_history_page, backend):
    _launch_history(coin_history_page)
    transactions = coin_history_page.transactions()
    debits = [tx for tx in transactions if tx.is_debit]
    if len(debits) < 2:
        pytest.skip("The current user has fewer than two deduction transactions")

    assert len({_tx_key(tx) for tx in debits}) == len(debits), (
        "Two deductions were merged into one transaction"
    )
    for transaction in debits:
        assert transaction.amount > 0
        assert transaction.type != "unknown", (
            f"Deduction has no transaction type: {transaction.raw!r}"
        )

    assert coin_history_page.balance() >= 0, "Coin balance became negative"
    assert not coin_history_page.duplicate_transactions(transactions), (
        "Duplicate deduction transactions are present"
    )
    backend_duplicates = backend.find_duplicate_transactions()
    assert not backend_duplicates, f"Backend has duplicate deductions: {backend_duplicates}"
    coin_history_page.assert_balance_consistent(transactions)


# ---------------------------------------------------------------------------
# Flow 4 - Insufficient coins
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.negative
def test_flow_04_insufficient_coins_blocks_deduction(
    coin_actions, coin_history_page, backend
):
    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)

    balance = coin_history_page.balance()
    assert balance is not None
    costs = {
        kind: _settings_amount(backend, kind)
        for kind in FEATURE_LABELS
    }
    unaffordable = [
        kind for kind, cost in costs.items() if cost is not None and cost > balance
    ]
    if not unaffordable:
        pytest.skip(
            f"The current balance ({balance}) covers every configured feature; "
            "insufficient-coins state cannot be forced"
        )

    before = coin_history_page.transactions()
    for kind in unaffordable:
        result = _trigger_deduction(coin_actions, kind)
        if not result.attempted:
            continue
        if result.status == "feature_unavailable":
            continue
        assert result.status == "insufficient_coins" or coin_history_page.has_insufficient_coins_message(), (
            f"{FEATURE_LABELS[kind]} proceeded without enough coins: {result.status}"
        )
        if not coin_history_page.is_purchase_page():
            coin_history_page.open_purchase()
        assert coin_history_page.is_purchase_page(), (
            "The user was not redirected to the Coin Purchase page"
        )
        _open_history_after_action(coin_history_page)
        assert coin_history_page.balance() == balance, "Balance changed after a blocked deduction"
        assert not [
            tx for tx in _new_transactions(before, coin_history_page.transactions())
            if tx.type == kind
        ], f"Coin History recorded a deduction for a failed {kind} request"
        return

    pytest.skip("None of the unaffordable features could be opened")


# ---------------------------------------------------------------------------
# Flow 5 - Not checked in
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.negative
def test_flow_05_not_checked_in_blocks_features(coin_actions, coin_history_page):
    _launch_history(coin_history_page)
    if coin_actions.open_bar() and coin_actions.is_checked_in():
        pytest.skip("The current user is already checked in; the not-checked-in state cannot be forced")

    before = coin_history_page.transactions()
    balance = coin_history_page.balance()
    attempted = False
    for kind in FEATURE_LABELS:
        result = _trigger_deduction(coin_actions, kind)
        if not result.attempted:
            continue
        attempted = True
        if result.status == "feature_unavailable":
            continue
        assert result.status == "not_checked_in" or coin_history_page.has_not_checked_in_message(), (
            f"{FEATURE_LABELS[kind]} opened for a user who is not checked in"
        )
        _open_history_after_action(coin_history_page)
        assert coin_history_page.balance() == balance, "Balance changed without a check-in"
        assert not [
            tx for tx in _new_transactions(before, coin_history_page.transactions())
            if tx.type == kind
        ], f"Coin History recorded a deduction for {kind} without a check-in"
        return
    if not attempted:
        pytest.skip("No coin feature was reachable for the not-checked-in test")
    pytest.skip("All reachable features were disabled; check-in requirement was not observable")


@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.negative
def test_flow_05_pending_or_rejected_checkin_blocks_features(
    coin_actions, coin_history_page
):
    _launch_history(coin_history_page)
    before = coin_history_page.transactions()
    result = coin_actions.check_in()
    if not result.attempted:
        pytest.skip(f"Could not reach the check-in flow: {result.message}")
    if result.status not in ("pending", "rejected"):
        pytest.skip("This bar auto-approves check-ins; pending/rejected state cannot be forced")

    feature = _trigger_deduction(coin_actions, "skip_the_queue")
    if not feature.attempted:
        pytest.skip(f"Skip the Queue is not reachable: {feature.message}")
    assert feature.status == "not_checked_in" or coin_history_page.has_not_checked_in_message(), (
        f"A coin feature opened while check-in was {result.status}"
    )
    _open_history_after_action(coin_history_page)
    assert not [
        tx for tx in _new_transactions(before, coin_history_page.transactions())
        if tx.type == "skip_the_queue"
    ], "Coins were deducted while the check-in was pending/rejected"


# ---------------------------------------------------------------------------
# Flow 6 - Feature disabled
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_deductions
@pytest.mark.negative
def test_flow_06_disabled_feature_blocks_deduction(
    coin_actions, coin_history_page, backend
):
    feature = CoinSettings.DISABLED_FEATURE.strip().lower().replace(" ", "_")
    if feature not in FEATURE_LABELS:
        pytest.skip(
            "Set COIN_DISABLED_FEATURE to skip_the_queue, song_request, "
            "shoutout_request or game_entry"
        )

    _launch_history(coin_history_page)
    _checked_in_or_skip(coin_actions)
    before = coin_history_page.transactions()
    balance = coin_history_page.balance()

    result = _trigger_deduction(coin_actions, feature)
    if not result.attempted:
        pytest.skip(f"{FEATURE_LABELS[feature]} is not reachable: {result.message}")
    if result.status == "feature_unavailable" or coin_history_page.has_feature_unavailable_message():
        _open_history_after_action(coin_history_page)
        assert coin_history_page.balance() == balance, "Balance changed for a disabled feature"
        assert not [
            tx for tx in _new_transactions(before, coin_history_page.transactions())
            if tx.type == feature
        ], f"Coin History recorded a deduction for disabled {feature}"
        return
    pytest.fail(
        f"{FEATURE_LABELS[feature]} was not blocked while configured as disabled: "
        f"{result.status}"
    )


# ---------------------------------------------------------------------------
# Flow 7 - Referral eligibility
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.signup
@pytest.mark.negative
def test_flow_07_invalid_referral_is_not_rewarded(driver, coin_history_page, backend):
    if not CoinSettings.INVALID_REFERRAL_CODE:
        pytest.skip("Set COIN_INVALID_REFERRAL_CODE")

    mobile = _signup_mobile()
    with _preserve_session(driver):
        try:
            mobile, _ = _register_new_user(
                driver,
                referral_code=CoinSettings.INVALID_REFERRAL_CODE,
                require_referral=False,
                mobile=mobile,
            )
        except Exception:
            # The correct behaviour for an invalid code can be to reject the
            # signup/OTP step outright. In that case there is no new user to
            # inspect, and no reward must have been created.
            assert not backend.get_reward_documents(
                "referral_registration_bonus", user=mobile
            ), "The backend created a referral reward for a rejected invalid code"
            return

        _launch_history(coin_history_page)
        assert not coin_history_page.find_transactions(
            "referral_registration_bonus"
        ), "An invalid referral code produced a Referral Registration Bonus"
        assert not coin_history_page.find_transactions("referral_bonus"), (
            "An invalid referral code produced a Referral Bonus"
        )
        assert not backend.get_reward_documents(
            "referral_registration_bonus", user=mobile
        ), "The backend created a referral reward for an invalid code"


# ---------------------------------------------------------------------------
# Flow 8 - Profile completion eligibility
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_credits
@pytest.mark.signup
@pytest.mark.negative
def test_flow_08_profile_completion_without_checkin_not_rewarded(
    driver, coin_actions, coin_history_page, backend
):
    with _preserve_session(driver):
        mobile, _ = _register_new_user(driver)
        coin_actions.open_bar()
        if coin_actions.is_checked_in():
            pytest.skip("The new user is already checked in; the eligibility split cannot be tested")

        result = coin_actions.complete_profile()
        if not result.attempted:
            pytest.skip(f"Profile completion is not reachable: {result.message}")

        _launch_history(coin_history_page)
        assert not coin_history_page.find_transactions(
            "profile_completion_bonus"
        ), "Profile Completion Bonus was credited without the required check-in"
        assert not backend.get_reward_documents(
            "profile_completion_bonus", user=mobile
        ), "The backend created a profile completion reward without a check-in"


# ---------------------------------------------------------------------------
# Flow 9 - Integrity and retry safety
# ---------------------------------------------------------------------------

@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.smoke
def test_flow_09_balance_history_and_backend_stay_consistent(
    coin_history_page, backend
):
    status = _launch_history(coin_history_page)
    if status == "empty":
        pytest.skip("The current user has no coin transactions to validate")
    transactions = coin_history_page.transactions()
    assert transactions

    balance = coin_history_page.balance()
    backend_balance = backend.get_user_balance()
    if backend_balance is not None:
        assert balance == backend_balance, (
            f"UI balance {balance} != backend balance {backend_balance}"
        )
    assert balance is not None and balance >= 0
    _assert_ui_matches_backend(coin_history_page, backend, transactions)
    assert not coin_history_page.duplicate_transactions(transactions), (
        "Coin History contains duplicate transactions"
    )
    assert not backend.find_duplicate_transactions(), (
        "The backend contains duplicate coin transactions"
    )

    backend_all = backend.get_coin_history(successful_only=False)
    failed = [transaction for transaction in backend_all if not transaction["successful"]]
    ui_text = " ".join(transaction.raw for transaction in transactions).lower()
    for transaction in failed:
        reference = transaction.get("reference")
        if reference:
            assert reference.lower() not in ui_text, (
                f"A failed transaction ({reference}) is shown as successful in Coin History"
            )


@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.positive
def test_flow_09_retries_do_not_duplicate_transactions(coin_history_page, backend):
    _launch_history(coin_history_page)
    baseline = [_tx_key(tx) for tx in coin_history_page.transactions()]

    for _ in range(3):
        coin_history_page.refresh()
        current = [_tx_key(tx) for tx in coin_history_page.transactions()]
        assert current == baseline, "A refresh/retry created a duplicate coin transaction"

    first = backend.get_coin_history()
    second = backend.get_coin_history()
    assert len(first) == len(second), "Retrying the history API changed the record count"
    assert not backend.find_duplicate_transactions(first), (
        "Retried API calls created duplicate backend transactions"
    )


# ---------------------------------------------------------------------------
# Flow 10 - ABO Settings configuration
# ---------------------------------------------------------------------------

def test_flow_10_coin_configuration_values_are_valid(backend):
    settings = backend.get_coin_settings()
    missing = [
        kind for kind in CoinSettings.SETTINGS_FIELDS if settings.get(kind) is None
    ]
    assert not missing, (
        "ABO Settings is missing or has an invalid value for: " + ", ".join(missing)
    )
    for kind, amount in settings.items():
        if kind == "_raw":
            continue
        assert amount is not None and amount >= 0, (
            f"{kind} must be a non-negative integer coin amount, got {amount!r}"
        )
        assert kind in CoinSettings.TRANSACTION_DIRECTIONS, (
            f"{kind} has no credit/debit mapping"
        )
        # The client-side fallback must not disagree with ABO Settings, or the
        # app and backend would apply different amounts.
        fallback = CoinSettings.configured_amount(kind)
        if fallback is not None:
            assert fallback == amount, (
                f"{kind} fallback is {fallback} but ABO Settings says {amount}"
            )


def test_flow_10_invalid_coin_amounts_are_rejected():
    invalid_values = (None, "", " ", "abc", "N/A", "null", -1, -5.0, 1.5, True, False)
    for value in invalid_values:
        assert CoinSettings.normalize_amount(value) is None, (
            f"Invalid coin amount {value!r} was accepted"
        )

    assert CoinSettings.normalize_amount("2") == 2
    assert CoinSettings.normalize_amount("2,000") == 2000
    assert CoinSettings.normalize_amount(2.0) == 2
    assert CoinSettings.normalize_amount(0) == 0


@pytest.mark.coins
@pytest.mark.coin_history
@pytest.mark.positive
def test_flow_10_existing_transactions_are_not_rewritten(coin_history_page):
    status = _launch_history(coin_history_page)
    if status == "empty":
        pytest.skip("No existing transactions to validate")
    before = [_tx_key(tx) for tx in coin_history_page.transactions()]
    coin_history_page.refresh()
    after = [_tx_key(tx) for tx in coin_history_page.transactions()]
    assert after == before, (
        "Refreshing after a settings read changed the historical transaction amounts"
    )


# ---------------------------------------------------------------------------
# Parser unit tests (device-free)
# ---------------------------------------------------------------------------

def test_coin_parser_credit_transaction():
    transaction = coin_parser.parse_transaction_text(
        "Signup Bonus\n+50 Coins\n02 Nov 2026, 10:30 AM\nBalance: 150"
    )
    assert transaction is not None
    assert transaction.type == "signup_bonus"
    assert transaction.direction == "credit"
    assert transaction.amount == 50
    assert transaction.balance_after == 150
    assert transaction.occurred_at is not None
    assert transaction.occurred_at.year == 2026


def test_coin_parser_debit_transaction():
    transaction = coin_parser.parse_transaction_text(
        "Skip the Queue\n-5 Coins\n02/11/2026 11:15\nBalance: 145"
    )
    assert transaction is not None
    assert transaction.type == "skip_the_queue"
    assert transaction.direction == "debit"
    assert transaction.amount == 5
    assert transaction.balance_after == 145


def test_coin_parser_profile_and_referral_types():
    profile = coin_parser.parse_transaction_text(
        "Profile Completion Bonus\n+10 coins\n03 Nov 2026\nBalance: 160"
    )
    referral = coin_parser.parse_transaction_text(
        "Referral Registration Bonus\n+20 coins\n03 Nov 2026\nBalance: 180"
    )
    assert profile and profile.type == "profile_completion_bonus"
    assert referral and referral.type == "referral_registration_bonus"


def test_coin_parser_rejects_non_transactions():
    assert coin_parser.parse_transaction_text("Coin Balance: 100") is None
    assert coin_parser.parse_transaction_text("Coin History") is None
    assert coin_parser.parse_transaction_text("") is None


def test_coin_parser_chronological_order():
    newest = coin_parser.parse_transaction_text(
        "Signup Bonus\n+2 coins\n02 Nov 2026 10:00\nBalance: 12"
    )
    older = coin_parser.parse_transaction_text(
        "Check-in Bonus\n+10 coins\n01 Nov 2026 09:00\nBalance: 10"
    )
    assert newest and older
    assert not coin_parser.chronological_errors([newest, older], newest_first=True)
    assert coin_parser.chronological_errors([older, newest], newest_first=True)


def test_coin_parser_balance_walk():
    newest = coin_parser.parse_transaction_text(
        "Signup Bonus\n+2 coins\n02 Nov 2026 10:00\nBalance: 12"
    )
    older = coin_parser.parse_transaction_text(
        "Check-in Bonus\n+10 coins\n01 Nov 2026 09:00\nBalance: 10"
    )
    assert newest and older
    assert not coin_parser.balance_errors(
        [newest, older], displayed_balance=12, newest_first=True
    )
    newest.balance_after = 13
    assert coin_parser.balance_errors(
        [newest, older], displayed_balance=12, newest_first=True
    )


def test_backend_transaction_normalisation():
    from utils.api_helpers import AboBackendClient

    credit = AboBackendClient.normalize_transaction(
        {
            "name": "TX-1",
            "amount": 2,
            "transaction_type": "Game Win Bonus",
            "creation": "2026-11-02 11:00:00",
            "status": "completed",
        }
    )
    debit = AboBackendClient.normalize_transaction(
        {
            "name": "TX-2",
            "amount": -1,
            "transaction_type": "Game Entry",
            "creation": "2026-11-02 11:05:00",
            "status": "completed",
        }
    )
    cancelled = AboBackendClient.normalize_transaction(
        {
            "name": "TX-3",
            "amount": 5,
            "transaction_type": "Song Request",
            "status": "cancelled",
        }
    )
    assert credit["direction"] == "credit" and credit["amount"] == 2
    assert debit["direction"] == "debit" and debit["amount"] == 1
    assert cancelled["successful"] is False


def test_coin_parser_duplicate_detection():
    first = coin_parser.parse_transaction_text(
        "Game Win Bonus\n+2 coins\n02 Nov 2026 10:00\nBalance: 12"
    )
    second = coin_parser.parse_transaction_text(
        "Game Win Bonus\n+2 coins\n02 Nov 2026 10:00\nBalance: 12"
    )
    different = coin_parser.parse_transaction_text(
        "Game Win Bonus\n+2 coins\n03 Nov 2026 10:00\nBalance: 14"
    )
    assert first and second and different
    duplicates = coin_parser.duplicates([first, second, different])
    assert len(duplicates) == 1
