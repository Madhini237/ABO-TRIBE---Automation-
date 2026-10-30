import os


def _env_flag(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


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
    SEARCH_CITY = os.getenv("LOCATION_SEARCH_CITY", "Pune")
    SEARCH_CITY_REGION = os.getenv("LOCATION_SEARCH_CITY_REGION", "Maharastra")
    INVALID_QUERY = os.getenv("LOCATION_INVALID_QUERY", "zzzzqqqq")
    # Leave empty when the backend has no known empty location. Flow 11 is then
    # reported as skipped rather than asserting a false negative.
    NO_BARS_CITY = os.getenv("LOCATION_NO_BARS_CITY", "")

    # Restore device permission / location / network state after tests that
    # deliberately change it.
    RESTORE_DEVICE_STATE = _env_flag("LOCATION_RESTORE_DEVICE_STATE", True)
    # On a physical device the nearest city returned by GPS is not controllable;
    # tests assert a successful detection instead of a hard-coded city unless
    # this value is set explicitly.
    EXPECTED_AUTO_CITY = os.getenv("LOCATION_EXPECTED_AUTO_CITY", "")
