import os


def _env_flag(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


def _env_list(name, default):
    value = os.getenv(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


class LocationSettings:
    """Runtime settings for the location and nearby-bars flows."""

    APP_PACKAGE = os.getenv("APP_PACKAGE", "com.coredot.abo.abo_bar")
    APP_ACTIVITY = os.getenv("APP_ACTIVITY", ".MainActivity")
    APP_COMPONENT = f"{APP_PACKAGE}/{APP_PACKAGE}.MainActivity"

    # Timeouts (seconds)
    HOME_TIMEOUT = int(os.getenv("LOCATION_HOME_TIMEOUT", "30"))
    SEARCH_TIMEOUT = int(os.getenv("LOCATION_SEARCH_TIMEOUT", "12"))
    GPS_TIMEOUT = int(os.getenv("LOCATION_GPS_TIMEOUT", "30"))
    BARS_TIMEOUT = int(os.getenv("LOCATION_BARS_TIMEOUT", "20"))
    NETWORK_TIMEOUT = int(os.getenv("LOCATION_NETWORK_TIMEOUT", "25"))
    SETTINGS_TIMEOUT = int(os.getenv("LOCATION_SETTINGS_TIMEOUT", "20"))
    MAX_SCROLLS = int(os.getenv("LOCATION_MAX_SCROLLS", "8"))

    # Locations used by the flows. Keep these overridable so the suite can be
    # pointed at another test city without editing code.
    DEFAULT_CITY = os.getenv("LOCATION_DEFAULT_CITY", "Coimbatore")
    DEFAULT_REGION = os.getenv("LOCATION_DEFAULT_REGION", "Tamil Nadu")
    ALTERNATIVE_CITY = os.getenv("LOCATION_ALTERNATIVE_CITY", "Kanyakumari")
    ALTERNATIVE_REGION = os.getenv("LOCATION_ALTERNATIVE_REGION", "Tamil Nadu")
    DUPLICATE_CITY = os.getenv("LOCATION_DUPLICATE_CITY", "Coonoor")
    DUPLICATE_REGIONS = _env_list(
        "LOCATION_DUPLICATE_REGIONS", ["Tamil Nadu", "Tamilnadu"]
    )
    SEARCH_CITY = os.getenv("LOCATION_SEARCH_CITY", "Pune")
    SEARCH_CITY_REGION = os.getenv("LOCATION_SEARCH_CITY_REGION", "Maharastra")
    LOCALITY_QUERY = os.getenv("LOCATION_LOCALITY_QUERY", "RS Puram")
    LOCALITY_PARENT_CITY = os.getenv("LOCATION_LOCALITY_PARENT_CITY", "Coimbatore")
    LANDMARK_QUERY = os.getenv("LOCATION_LANDMARK_QUERY", "Gandhipuram Bus Stand")
    LANDMARK_PARENT_CITY = os.getenv("LOCATION_LANDMARK_PARENT_CITY", "Coimbatore")
    INVALID_QUERY = os.getenv("LOCATION_INVALID_QUERY", "zzzzqqqq")
    # Leave empty when the backend has no known empty location. Flow 11 is then
    # reported as skipped rather than asserting a false negative.
    NO_BARS_CITY = os.getenv("LOCATION_NO_BARS_CITY", "")

    # Accuracy checks. Bars further than this from the selected city almost
    # certainly have wrong coordinates or belong to another city.
    MAX_BAR_RADIUS_KM = float(os.getenv("LOCATION_MAX_BAR_RADIUS_KM", "100"))
    EXCLUDED_BAR_MARKERS = _env_list(
        "LOCATION_EXCLUDED_BAR_MARKERS", ["deleted", "demo"]
    )
    NON_CUSTOMER_BAR_MARKERS = _env_list(
        "LOCATION_NON_CUSTOMER_BAR_MARKERS",
        ["test", "dummy", "staff", "internal", "inactive", "disabled", "draft", "hidden"],
    )
    EXCLUDED_BAR_NAMES = _env_list("LOCATION_EXCLUDED_BAR_NAMES", [])

    # Used by the API-failure tests: an unreachable HTTP proxy keeps the device
    # "online" while every backend call fails.
    API_FAILURE_PROXY = os.getenv("LOCATION_API_FAILURE_PROXY", "127.0.0.1:1")
    GPS_TIMEOUT_MARGIN = int(os.getenv("LOCATION_GPS_TIMEOUT_MARGIN", "15"))

    # Restore device permission / location / network state after tests that
    # deliberately change it.
    RESTORE_DEVICE_STATE = _env_flag("LOCATION_RESTORE_DEVICE_STATE", True)
    # On a physical device the nearest city returned by GPS is not controllable;
    # tests assert a successful detection instead of a hard-coded city unless
    # this value is set explicitly.
    EXPECTED_AUTO_CITY = os.getenv("LOCATION_EXPECTED_AUTO_CITY", "")


class CoinSettings:
    """Runtime settings for the coin wallet, history and reward flows.

    Coin amounts are configured in the backend (ABO Settings doctype). The
    environment values below are only a fallback for UI-only runs where the
    backend API is not configured; they must match the active ABO Settings
    values when used.
    """

    APP_PACKAGE = LocationSettings.APP_PACKAGE
    APP_COMPONENT = LocationSettings.APP_COMPONENT

    # Timeouts (seconds)
    TIMEOUT = int(os.getenv("COIN_TIMEOUT", "20"))
    OPEN_TIMEOUT = int(os.getenv("COIN_OPEN_TIMEOUT", "20"))
    HISTORY_TIMEOUT = int(os.getenv("COIN_HISTORY_TIMEOUT", "25"))
    ACTION_TIMEOUT = int(os.getenv("COIN_ACTION_TIMEOUT", "20"))
    FEEDBACK_TIMEOUT = int(os.getenv("COIN_FEEDBACK_TIMEOUT", "12"))
    MAX_SCROLLS = int(os.getenv("COIN_HISTORY_MAX_SCROLLS", "8"))

    # Most wallets show the newest transaction first. Set this to false when
    # the backend/app changes the sort direction.
    NEWEST_FIRST = _env_flag("COIN_HISTORY_NEWEST_FIRST", True)

    # A transaction without a visible timestamp cannot be chronologically
    # verified. Keep this false so a missing date/time is a real failure.
    ALLOW_MISSING_TIMESTAMPS = _env_flag(
        "COIN_ALLOW_MISSING_TIMESTAMPS", False
    )

    # ------------------------------------------------------- transaction types
    TRANSACTION_DIRECTIONS = {
        "signup_bonus": "credit",
        "checkin_bonus": "credit",
        "referral_registration_bonus": "credit",
        "referral_bonus": "credit",
        "profile_completion_bonus": "credit",
        "game_win_bonus": "credit",
        "coin_purchase": "credit",
        "refund": "credit",
        "skip_the_queue": "debit",
        "song_request": "debit",
        "shoutout_request": "debit",
        "game_entry": "debit",
    }

    TRANSACTION_ALIASES = {
        "signup_bonus": ("signup bonus", "sign up bonus", "welcome bonus"),
        "checkin_bonus": (
            "check-in bonus",
            "checkin bonus",
            "check in bonus",
            "check-in reward",
        ),
        "referral_registration_bonus": (
            "referral registration bonus",
            "referral signup bonus",
            "referral registration",
        ),
        "referral_bonus": (
            "referral bonus",
            "referral reward",
            "successful referral",
        ),
        "profile_completion_bonus": (
            "profile completion bonus",
            "profile complete bonus",
            "profile completion",
        ),
        "game_win_bonus": (
            "game win bonus",
            "game win",
            "win bonus",
            "game winning",
        ),
        "skip_the_queue": (
            "skip the queue",
            "skip queue",
            "skip-the-queue",
        ),
        "song_request": ("song request", "song-request"),
        "shoutout_request": (
            "shoutout request",
            "shout out request",
            "shoutout",
            "shout out",
        ),
        "game_entry": (
            "game entry",
            "game-entry",
            "entry fee",
            "game fee",
        ),
        "coin_purchase": ("coin purchase", "buy coins", "coins purchased"),
        "refund": ("refund", "coins refunded"),
    }

    # ------------------------------------------------------ ABO Settings fields
    # The first matching field wins. Keep every known spelling here so a
    # backend rename does not silently fall back to a stale amount.
    SETTINGS_FIELDS = {
        "signup_bonus": (
            "signup_bonus_coin",
            "signup_bonus_coins",
            "signup_bonus",
        ),
        "checkin_bonus": (
            "checkin_bonus_coin",
            "check_in_bonus_coin",
            "checkin_bonus_coins",
            "checkin_bonus",
        ),
        "referral_registration_bonus": (
            "referral_registration_bonus_coin",
            "referral_registration_coin",
            "referral_bonus_coin",
            "referral_bonus",
        ),
        "referral_bonus": (
            "referral_bonus_coin",
            "referral_reward_coin",
            "referral_bonus",
        ),
        "profile_completion_bonus": (
            "profile_complete_coin",
            "profile_completion_coin",
            "profile_complete_bonus_coin",
        ),
        "game_entry": (
            "game_entry_coin",
            "game_entry_coins",
            "per_game_coins",
        ),
        "game_win_bonus": (
            "game_win_bonus_coin",
            "game_win_coin",
            "game_win_bonus",
        ),
        "skip_the_queue": (
            "skip_the_queue_coin",
            "skip_queue_coin",
            "skip_the_queue_coin_deduct",
        ),
        "song_request": (
            "song_request_coin",
            "song_request_coins",
            "song_request_coin_deduct",
        ),
        "shoutout_request": (
            "shoutout_request_coin",
            "shoutout_coin",
            "shoutout_request_coin_deduct",
        ),
    }

    # Backend doctypes used to prove that the matching record was created.
    BACKEND_DOCTYPES = {
        "signup_bonus": "signup_bonus_coin",
        "checkin_bonus": "checkin_bonus_coin",
        "referral_registration_bonus": "referral_bonus_coin",
        "referral_bonus": "referral_bonus_coin",
        "profile_completion_bonus": "profile_completion_coin",
        "game_entry": "per_game_coins",
        "game_win_bonus": "per_game_coins",
        "skip_the_queue": "skip_the_queue_coin_deduct",
        "song_request": "song_request_coin_deduct",
        "shoutout_request": "shoutout_request_coin_deduct",
    }

    # Optional UI-only fallbacks. When set, positive flows assert the exact
    # amount. When unset, the amount is read from ABO Settings through the API.
    ENV_AMOUNTS = {
        "signup_bonus": os.getenv("COIN_SIGNUP_BONUS"),
        "checkin_bonus": os.getenv("COIN_CHECKIN_BONUS"),
        "referral_registration_bonus": os.getenv(
            "COIN_REFERRAL_REGISTRATION_BONUS"
        ),
        "referral_bonus": os.getenv("COIN_REFERRAL_BONUS"),
        "profile_completion_bonus": os.getenv("COIN_PROFILE_COMPLETE"),
        "game_entry": os.getenv("COIN_GAME_ENTRY"),
        "game_win_bonus": os.getenv("COIN_GAME_WIN_BONUS"),
        "skip_the_queue": os.getenv("COIN_SKIP_THE_QUEUE"),
        "song_request": os.getenv("COIN_SONG_REQUEST"),
        "shoutout_request": os.getenv("COIN_SHOUTOUT_REQUEST"),
    }

    # ------------------------------------------------------------- UI messages
    HISTORY_TITLE_MARKERS = (
        "coin history",
        "coins history",
        "transaction history",
        "history",
        "transactions",
    )
    BALANCE_MARKERS = (
        "coin balance",
        "available coins",
        "available balance",
        "total coins",
        "my coins",
        "balance",
    )
    CREDIT_MARKERS = (
        "credit",
        "credited",
        "earned",
        "added",
        "received",
        "reward",
        "bonus",
        "won",
        "refund",
        "cashback",
        "+",
    )
    DEBIT_MARKERS = (
        "debit",
        "debited",
        "deducted",
        "deduction",
        "spent",
        "used",
        "redeemed",
        "entry",
        "request",
        "purchase",
        "-",
    )
    EMPTY_MARKERS = (
        "no coin history",
        "no transactions",
        "no transaction history",
        "haven't earned",
        "have not earned",
        "nothing here yet",
        "no activity",
    )
    ERROR_MARKERS = (
        "unable to load",
        "failed to load",
        "couldn't load",
        "could not load",
        "something went wrong",
        "try again",
        "no internet",
        "offline",
        "network error",
    )
    RETRY_MARKERS = ("retry", "try again", "refresh")
    INSUFFICIENT_MARKERS = (
        "insufficient coin",
        "insufficient balance",
        "not enough coin",
        "not enough balance",
        "you don't have enough",
        "you do not have enough",
    )
    NOT_CHECKED_IN_MARKERS = (
        "not checked in",
        "not checked-in",
        "check in to",
        "check-in to",
        "please check in",
        "please check-in",
        "check-in required",
        "check in required",
        "you must be checked in",
    )
    FEATURE_DISABLED_MARKERS = (
        "feature currently unavailable",
        "currently unavailable",
        "feature unavailable",
        "not available",
        "disabled",
        "turned off",
        "not enabled",
    )
    PURCHASE_MARKERS = (
        "coin purchase",
        "buy coins",
        "purchase coins",
        "recharge",
        "add coins",
        "top up",
        "top-up",
    )
    CHECKIN_PENDING_MARKERS = (
        "pending",
        "waiting for approval",
        "approval pending",
        "request sent",
    )
    CHECKIN_REJECTED_MARKERS = (
        "rejected",
        "declined",
        "check-in failed",
        "check in failed",
    )
    CHECKIN_SUCCESS_MARKERS = (
        "checked in",
        "check-in successful",
        "check in successful",
        "you're in",
        "you are in",
    )
    CHECKED_IN_MARKERS = (
        "checked in",
        "checked-in",
        "you're checked in",
        "you are checked in",
    )

    # ------------------------------------------- optional flow test data/env
    # Used by positive credit/deduction flows. When these are blank the test
    # skips instead of accidentally acting on an unrelated bar.
    BAR_NAME = os.getenv("COIN_BAR_NAME", "")
    GAME_NAME = os.getenv("COIN_GAME_NAME", "")
    SONG_NAME = os.getenv("COIN_SONG_NAME", "Test Song")
    SHOUTOUT_MESSAGE = os.getenv("COIN_SHOUTOUT_MESSAGE", "Test shoutout")
    REFERRAL_CODE = os.getenv("COIN_REFERRAL_CODE", "")
    INVALID_REFERRAL_CODE = os.getenv(
        "COIN_INVALID_REFERRAL_CODE", "INVALID-REFERRAL"
    )
    SIGNUP_MOBILE = os.getenv("COIN_SIGNUP_MOBILE", "")
    SIGNUP_OTP = os.getenv("COIN_SIGNUP_OTP", "")
    REFERRER_MOBILE = os.getenv("COIN_REFERRER_MOBILE", "")
    REFERRER_OTP = os.getenv("COIN_REFERRER_OTP", "")
    OTHER_USER_MOBILE = os.getenv("COIN_OTHER_USER_MOBILE", "")
    DISABLED_FEATURE = os.getenv("COIN_DISABLED_FEATURE", "")
    PROFILE_DATA = os.getenv("SIGNUP_PROFILE_DATA", "{}")

    # A game win is probabilistic. Keep this small: every attempt spends the
    # configured game-entry coins.
    GAME_WIN_ATTEMPTS = int(os.getenv("COIN_GAME_WIN_ATTEMPTS", "3"))

    # API-failure simulation reuses the unreachable proxy from the location
    # suite, which keeps the device online while backend requests fail.
    API_FAILURE_PROXY = os.getenv(
        "COIN_API_FAILURE_PROXY", LocationSettings.API_FAILURE_PROXY
    )

    # --------------------------------------------------------------- helpers
    @staticmethod
    def normalize_amount(value):
        """Return a non-negative integer coin amount, or None when invalid."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, float):
            if value < 0 or not value.is_integer():
                return None
            return int(value)
        text = str(value).strip().replace(",", "")
        if not text or text.lower() in ("none", "null", "nan", "n/a", "-"):
            return None
        try:
            number = float(text)
        except (TypeError, ValueError):
            return None
        if number < 0 or not number.is_integer():
            return None
        return int(number)

    @classmethod
    def configured_amount(cls, transaction_type):
        return cls.normalize_amount(cls.ENV_AMOUNTS.get(transaction_type))
