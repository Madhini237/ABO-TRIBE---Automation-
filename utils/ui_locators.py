# UI Locators for ABO TRIBE Automation (Mobile/Appium)
# Centralized locators to keep Page Objects clean

class LoginLocators:
    # Phone Number Screen - Based on actual app inspection
    PHONE_INPUT = ("xpath", "//android.widget.EditText[@hint='10-digit mobile number']")
    PHONE_INPUT_XPATH = ("xpath", "//android.widget.EditText[contains(@hint,'mobile') or contains(@hint,'Mobile') or contains(@text,'Phone')]")
    PHONE_INPUT_ACCESSIBILITY = ("xpath", "//android.widget.EditText")

    SEND_OTP_BTN = ("xpath", "//android.widget.Button[@content-desc='Login']")
    SEND_OTP_BTN_XPATH = ("xpath", "//android.widget.Button[@content-desc='Login' or contains(@content-desc,'Login') or contains(@text,'Login')]")
    SEND_OTP_BTN_ACCESSIBILITY = ("accessibility id", "Login")

    # OTP Screen
    OTP_INPUT = ("xpath", "//android.widget.EditText")
    OTP_INPUT_XPATH = ("xpath", "//android.widget.EditText")
    OTP_INPUT_ACCESSIBILITY = ("xpath", "//android.widget.EditText")

    VERIFY_BTN = ("xpath", "//android.widget.Button[contains(@content-desc,'Verify') or contains(@text,'Verify') or contains(@content-desc,'Submit') or contains(@text,'Submit')]")
    VERIFY_BTN_XPATH = ("xpath", "//android.widget.Button")
    VERIFY_BTN_ACCESSIBILITY = ("xpath", "//android.widget.Button")

    RESEND_BTN = ("xpath", "//android.widget.Button[contains(@content-desc,'Resend') or contains(@text,'Resend')]")
    RESEND_BTN_XPATH = ("xpath", "//android.widget.Button[contains(@content-desc,'Resend') or contains(@text,'Resend')]")
    RESEND_BTN_ACCESSIBILITY = ("xpath", "//android.widget.Button[contains(@content-desc,'Resend')]")

    # Messages / Screens
    ERROR_MSG = ("xpath", "//android.widget.TextView[contains(@text,'Invalid') or contains(@text,'invalid') or contains(@text,'Wrong') or contains(@text,'error')]")
    ERROR_MSG_XPATH = ("xpath", "//android.widget.TextView[contains(@text,'Invalid') or contains(@text,'invalid') or contains(@text,'Wrong')]")
    ERROR_MSG_ACCESSIBILITY = ("xpath", "//android.widget.TextView")

    OTP_SCREEN_INDICATOR = ("xpath", "//*[contains(@text,'Enter OTP') or contains(@text,'Verification') or contains(@text,'OTP') or contains(@text,'6')]")
    DASHBOARD_INDICATOR = ("xpath", "//*[contains(@text,'Home') or contains(@text,'Dashboard') or contains(@content-desc,'Home') or contains(@content-desc,'Dashboard')]")


class HomeLocators:
    DASHBOARD_ROOT = ("xpath", "//*[contains(@text,'Home') or contains(@text,'Dashboard')]")
    LOCATION_HEADER = ("xpath", "//*[@clickable='true' and @content-desc!='']")
    HOME_TAB = ("xpath", "//android.widget.Button[@content-desc='Home']")
    SEARCH_BAR = ("xpath", "//*[contains(@content-desc,'Search for')]")
    NEARBY_BARS_HEADING = ("xpath", "//*[contains(@content-desc,'Nearby Bars') or contains(@text,'Nearby Bars')]")


class LocationLocators:
    """Location selector, permission prompts and search feedback."""

    SCRIM = ("xpath", "//*[@content-desc='Scrim']")
    SEARCH_INPUT = ("xpath", "//android.widget.EditText[@hint='Search city, area or locality']")
    ANY_EDIT_TEXT = ("xpath", "//android.widget.EditText")
    RECENT_HEADER = ("xpath", "//*[contains(@content-desc,'Recently selected')]")
    OTHER_CITIES_HEADER = ("xpath", "//*[contains(@content-desc,'Other cities')]")
    SEARCH_RESULTS_HEADER = ("xpath", "//*[contains(@content-desc,'Search results')]")
    CURRENT_LOCATION = (
        "xpath",
        "//*[contains(@content-desc,'Use current location') or contains(@content-desc,'Using GPS')]",
    )
    PERMISSION_BANNER = (
        "xpath",
        "//*[contains(@content-desc,'Enable location permissions')]",
    )
    PERMISSION_PRIMER = (
        "xpath",
        "//*[contains(@content-desc,'Discover bars and offers near you')]",
    )
    PRIMER_ALLOW = ("xpath", "//android.widget.Button[@content-desc='Allow']")
    PRIMER_NOT_NOW = ("xpath", "//*[@content-desc='Not right now']")
    NOT_FOUND = (
        "xpath",
        "//*[contains(@content-desc,'No matching cities found') or "
        "contains(@text,'No matching cities found') or "
        "contains(@content-desc,'Location not found') or "
        "contains(@text,'Location not found') or "
        "contains(@content-desc,'No results found') or "
        "contains(@text,'No results found')]",
    )
    NETWORK_ERROR = (
        "xpath",
        "//*[contains(translate(@content-desc,'NETWORKOFFLINECONNECTION','networkofflineconnection'),'network') or "
        "contains(translate(@text,'NETWORKOFFLINECONNECTION','networkofflineconnection'),'network') or "
        "contains(translate(@content-desc,'NETWORKOFFLINECONNECTION','networkofflineconnection'),'offline') or "
        "contains(translate(@text,'NETWORKOFFLINECONNECTION','networkofflineconnection'),'offline') or "
        "contains(translate(@content-desc,'NETWORKOFFLINECONNECTION','networkofflineconnection'),'connection') or "
        "contains(translate(@text,'NETWORKOFFLINECONNECTION','networkofflineconnection'),'connection')]",
    )
    LOCATION_SERVICES_PROMPT = (
        "xpath",
        "//*[contains(translate(@content-desc,'LOCATIONSERVICES','locationservices'),'location services') or "
        "contains(translate(@text,'LOCATIONSERVICES','locationservices'),'location services') or "
        "contains(translate(@content-desc,'LOCATIONSERVICES','locationservices'),'turn on location') or "
        "contains(translate(@text,'LOCATIONSERVICES','locationservices'),'turn on location') or "
        "contains(translate(@content-desc,'LOCATIONSERVICES','locationservices'),'location is off') or "
        "contains(translate(@text,'LOCATIONSERVICES','locationservices'),'location is off')]",
    )
    PERMISSION_EXPLANATION = (
        "xpath",
        "//*[contains(translate(@content-desc,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'permission denied') or "
        "contains(translate(@text,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'permission denied') or "
        "contains(translate(@content-desc,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'open settings') or "
        "contains(translate(@text,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'open settings') or "
        "contains(translate(@content-desc,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'allow location') or "
        "contains(translate(@text,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'allow location') or "
        "contains(translate(@content-desc,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'location access') or "
        "contains(translate(@text,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'location access') or "
        "contains(translate(@content-desc,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'location not detected') or "
        "contains(translate(@text,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'location not detected') or "
        "contains(translate(@content-desc,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'enable them in settings') or "
        "contains(translate(@text,'LOCATIONPERMISSIONDENIEDSETTINGS','locationpermissiondeniedsettings'),'enable them in settings')]",
    )
    LOCATION_ERROR_TITLE = (
        "xpath",
        "//*[contains(@content-desc,'Location not detected') or contains(@text,'Location not detected')]",
    )
    GO_TO_SETTINGS = (
        "xpath",
        "//*[contains(@content-desc,'Go to settings') or contains(@text,'Go to settings')]",
    )
    RETRY = ("xpath", "//*[@content-desc='Retry' or @text='Retry' or @content-desc='Try again' or @text='Try again']")


class NearbyBarsLocators:
    """Eligible bars shown below the Most Visited / Top Picks section."""

    BAR_CARD = ("xpath", "//*[@clickable='true' and contains(@content-desc, '•')]")
    OFFLINE_BANNER = (
        "xpath",
        "//*[contains(@content-desc,\"You're Offline\") or contains(@text,\"You're Offline\") or "
        "contains(@content-desc,'You’re Offline') or contains(@text,'You’re Offline') or "
        "contains(@content-desc,'Showing saved') or contains(@text,'Showing saved')]",
    )
    RETRY = ("xpath", "//*[@content-desc='Retry' or @text='Retry' or @content-desc='Try again' or @text='Try again']")
    EMPTY_STATE = (
        "xpath",
        "//*[contains(translate(@content-desc,'NOBARS','nobars'),'no bars') or "
        "contains(translate(@text,'NOBARS','nobars'),'no bars') or "
        "contains(translate(@content-desc,'NOVENUES','novenues'),'no venues') or "
        "contains(translate(@text,'NOVENUES','novenues'),'no venues') or "
        "contains(translate(@content-desc,'NORESTAURANTS','norestaurants'),'no restaurants') or "
        "contains(translate(@text,'NORESTAURANTS','norestaurants'),'no restaurants')]",
    )
    ERROR_STATE = (
        "xpath",
        "//*[contains(translate(@content-desc,'UNABLETOLOADFAILED','unabletoloadfailed'),'unable to load') or "
        "contains(translate(@text,'UNABLETOLOADFAILED','unabletoloadfailed'),'unable to load') or "
        "contains(translate(@content-desc,'UNABLETOLOADFAILED','unabletoloadfailed'),'failed to load') or "
        "contains(translate(@text,'UNABLETOLOADFAILED','unabletoloadfailed'),'failed to load') or "
        "contains(translate(@content-desc,'UNABLETOLOADFAILED','unabletoloadfailed'),\"couldn't load\") or "
        "contains(translate(@text,'UNABLETOLOADFAILED','unabletoloadfailed'),\"couldn't load\")]",
    )


class AndroidSettingsLocators:
    """System Settings / permission-controller elements (Android 11+)."""

    APP_DETAILS_PERMISSIONS = ("xpath", "//android.widget.TextView[@text='Permissions']")
    APP_PERMISSIONS_TITLE = ("xpath", "//android.widget.TextView[@text='App permissions']")
    APP_LOCATION_ROW = ("xpath", "//android.widget.TextView[@text='Location']")
    LOCATION_PERMISSION_TITLE = ("xpath", "//android.widget.TextView[@text='Location permission']")
    LOCATION_ALLOW_FOREGROUND = ("id", "com.android.permissioncontroller:id/allow_foreground_only_radio_button")
    LOCATION_ALLOW_ASK = ("id", "com.android.permissioncontroller:id/ask_radio_button")
    LOCATION_DENY = ("id", "com.android.permissioncontroller:id/deny_radio_button")
    LOCATION_SWITCH = ("xpath", "//android.widget.Switch[@resource-id='android:id/switch_widget']")
    PRECISE_LOCATION_SWITCH = (
        "xpath",
        "//*[@resource-id='com.android.permissioncontroller:id/precise_location_switch' or "
        "(contains(@text,'Use precise location') and "
        "(@checkable='true' or @class='android.widget.Switch'))]",
    )

    SYSTEM_ALLOW_FOREGROUND = ("id", "com.android.permissioncontroller:id/permission_allow_foreground_only_button")
    SYSTEM_ALLOW_ONE_TIME = ("id", "com.android.permissioncontroller:id/permission_allow_one_time_button")
    SYSTEM_ALLOW = ("id", "com.android.permissioncontroller:id/permission_allow_button")
    SYSTEM_DENY = ("id", "com.android.permissioncontroller:id/permission_deny_button")
    SYSTEM_DENY_DONT_ASK = ("id", "com.android.permissioncontroller:id/permission_deny_and_dont_ask_again_button")


def _lower_contains(*needles):
    """Build a case-insensitive content-desc/text contains() XPath."""
    return (
        "xpath",
        "//*[" + " or ".join(
            "contains(translate(@content-desc,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
            f"'{needle.lower()}') or "
            "contains(translate(@text,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
            f"'{needle.lower()}')"
            for needle in needles
        ) + "]",
    )


def _lower_equals(*needles):
    """Build a case-insensitive content-desc/text equals() XPath."""
    return (
        "xpath",
        "//*[" + " or ".join(
            "translate(@content-desc,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')="
            f"'{needle.lower()}' or "
            "translate(@text,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')="
            f"'{needle.lower()}'"
            for needle in needles
        ) + "]",
    )


class CoinLocators:
    """Coin wallet and Coin History screen elements.

    The XPaths are deliberately text based: the wallet labels are rendered as
    content descriptions in the current build and do not have stable
    resource-ids. The page object also parses ``page_source`` directly so
    grouped transaction rows remain readable if the accessibility tree changes.
    """

    # Wallet entry / title
    COINS_ENTRY = _lower_contains("coin", "coin balance", "my coins")
    BALANCE = _lower_contains(
        "coin balance", "available coins", "total coins", "my coins", "balance"
    )
    HISTORY_ENTRY = _lower_contains("coin history", "transaction history", "history", "transactions")
    HISTORY_TITLE = _lower_contains("coin history", "transaction history", "transactions")
    HISTORY_LIST = (
        "xpath",
        "//androidx.recyclerview.widget.RecyclerView | "
        "//android.widget.ListView | "
        "//*[@scrollable='true']",
    )

    # Transaction rows (parsed from page source as well)
    TRANSACTION_ROW = (
        "xpath",
        "//*[@clickable='true' and ("
        "contains(@content-desc,'+') or contains(@content-desc,'-') or "
        "contains(@text,'+') or contains(@text,'-'))]",
    )
    CREDIT_INDICATOR = _lower_contains("credit", "credited", "earned", "added", "bonus")
    DEBIT_INDICATOR = _lower_contains("debit", "debited", "deducted", "spent", "used")

    # Page states
    EMPTY_STATE = _lower_contains(
        "no coin history",
        "no transactions",
        "no transaction history",
        "nothing here yet",
        "no activity",
        "haven't earned",
        "have not earned",
    )
    ERROR_STATE = _lower_contains(
        "unable to load",
        "failed to load",
        "couldn't load",
        "could not load",
        "something went wrong",
        "network error",
        "no internet",
        "you're offline",
        "you’re offline",
        "offline",
    )
    RETRY = _lower_equals("retry", "try again", "refresh")
    REFRESH = _lower_contains("refresh", "pull to refresh")
    BACK = _lower_equals("back", "close")
    USER_SWITCHER = _lower_contains("switch user", "switch account", "change user", "change account")
    PURCHASE_TITLE = _lower_contains(
        "coin purchase", "buy coins", "purchase coins", "add coins", "top up", "top-up", "recharge"
    )
    INSUFFICIENT_MESSAGE = _lower_contains(
        "insufficient coin",
        "insufficient balance",
        "not enough coin",
        "not enough balance",
        "you don't have enough",
        "you do not have enough",
    )
    NOT_CHECKED_IN_MESSAGE = _lower_contains(
        "not checked in",
        "not checked-in",
        "please check in",
        "please check-in",
        "check-in required",
        "check in required",
        "you must be checked in",
    )
    FEATURE_UNAVAILABLE_MESSAGE = _lower_contains(
        "feature currently unavailable",
        "currently unavailable",
        "feature unavailable",
        "not available",
        "disabled",
        "turned off",
        "not enabled",
    )
    CONFIRM = _lower_equals("confirm", "yes", "ok", "continue", "proceed")
    CANCEL = _lower_equals("cancel", "no", "close")


class CoinActionLocators:
    """Entry points used to earn or spend coins from the bar/home flows."""

    HOME_TAB = ("xpath", "//android.widget.Button[@content-desc='Home']")
    BAR_CARD = ("xpath", "//*[@clickable='true' and contains(@content-desc, '•')]")
    CHECK_IN_BUTTON = _lower_contains("check in", "check-in", "checkin")
    CHECKED_IN_BANNER = _lower_contains("checked in", "checked-in", "you're in", "you are in")
    CHECK_IN_PENDING = _lower_contains("check-in pending", "check in pending", "pending approval")
    CHECK_IN_REJECTED = _lower_contains("check-in rejected", "check in rejected", "rejected", "declined")
    CHECK_IN_SUCCESS = _lower_contains(
        "checked in successfully", "check-in successful", "check in successful", "you're checked in"
    )

    SKIP_THE_QUEUE = _lower_contains("skip the queue", "skip queue")
    SONG_REQUEST = _lower_contains("song request", "request a song")
    SHOUTOUT_REQUEST = _lower_contains("shoutout", "shout out")
    GAME = _lower_contains("game", "play")
    GAME_ENTRY = _lower_contains("game entry", "entry fee", "play game", "start game")
    GAME_PLAY = _lower_contains("play", "start", "roll", "dice")
    GAME_RESULT = _lower_contains("you won", "you win", "congratulations", "better luck", "you lost")

    FORM_INPUT = ("xpath", "//android.widget.EditText")
    SUBMIT = _lower_contains("submit", "send", "request", "confirm", "continue", "save")
    PROFILE_ENTRY = _lower_equals("profile", "my profile")
    EDIT_PROFILE = _lower_contains("edit profile", "edit")
    SAVE_PROFILE = _lower_contains("save", "update", "submit")
    MENU = _lower_equals("menu")
    HOME_MENU_TAP = (660, 107)  # icon beside the coins balance (see LoginPage.logout)

    COIN_PURCHASE = _lower_contains(
        "coin purchase", "buy coins", "purchase coins", "add coins", "top up", "top-up", "recharge"
    )
    PURCHASE_BUTTON = _lower_contains("buy", "purchase", "add coins", "recharge")
