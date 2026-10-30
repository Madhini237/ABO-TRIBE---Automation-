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

    SYSTEM_ALLOW_FOREGROUND = ("id", "com.android.permissioncontroller:id/permission_allow_foreground_only_button")
    SYSTEM_ALLOW_ONE_TIME = ("id", "com.android.permissioncontroller:id/permission_allow_one_time_button")
    SYSTEM_ALLOW = ("id", "com.android.permissioncontroller:id/permission_allow_button")
    SYSTEM_DENY = ("id", "com.android.permissioncontroller:id/permission_deny_button")
    SYSTEM_DENY_DONT_ASK = ("id", "com.android.permissioncontroller:id/permission_deny_and_dont_ask_again_button")
