import json
from pathlib import Path

import pytest

from appium import webdriver
from appium.options.android import UiAutomator2Options

from pages.coin_actions_page import CoinActionsPage
from pages.coin_history_page import CoinHistoryPage
from pages.location_page import LocationPage
from pages.nearby_bars_page import NearbyBarsPage
from utils.api_helpers import AboBackendClient
from utils.device_control import DeviceController


@pytest.fixture(scope="session")
def driver():

    options = UiAutomator2Options()

    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = "Android Device"

    # Your connected Android device
    options.udid = "PV5THY65BMNJ957S"

    # ABO Tribe application
    options.app_package = "com.coredot.abo.abo_bar"
    options.app_activity = "com.coredot.abo.abo_bar.MainActivity"

    options.no_reset = True
    options.set_capability(
        "appium:ignoreHiddenApiPolicyError", True
    )

    driver = webdriver.Remote(
        "http://127.0.0.1:4723",
        options=options
    )

    driver.implicitly_wait(0)

    yield driver

    driver.quit()


@pytest.fixture
def device(driver):
    return DeviceController(driver)


@pytest.fixture
def location_page(driver, device):
    return LocationPage(driver, device)


@pytest.fixture
def nearby_bars_page(driver):
    return NearbyBarsPage(driver)


@pytest.fixture
def app_home(location_page):
    """Start the app on the authenticated home screen.

    The suite reuses the signed-in session. If the app has been signed out,
    the test is skipped with a clear message instead of hiding the failure.
    """
    if not location_page.launch_app(handle_primer="dismiss"):
        if location_page.is_login_screen():
            pytest.skip("ABO Tribe is signed out; sign in before running location tests")
        raise AssertionError("Home screen did not load with a selected location")
    return location_page


@pytest.fixture
def preserve_device_state(device):
    """Capture permission, location and network state and restore it afterwards."""
    snapshot = device.snapshot()
    yield snapshot
    try:
        device.restore(snapshot)
    except Exception as error:  # restore is best-effort; never mask a test failure
        print(f"WARNING: could not fully restore device state: {error}")


# ---------------------------------------------------------------------------
# Coin wallet / Coin History fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def coin_history_page(driver, device):
    return CoinHistoryPage(driver, device=device)


@pytest.fixture
def coin_actions(driver):
    return CoinActionsPage(driver)


@pytest.fixture
def backend():
    """Backend client for balance, transaction and reward validation.

    Backend-only tests skip when ABO_API_BASE_URL is not configured instead of
    silently passing without checking the requirement.
    """
    client = AboBackendClient.from_env()
    if not client.configured:
        pytest.skip(
            "Set ABO_API_BASE_URL and ABO_API_TOKEN (or ABO_API_KEY/"
            "ABO_API_SECRET) to run backend coin validation"
        )
    return client


@pytest.fixture
def coin_data():
    path = Path(__file__).resolve().parent.parent / "test_data" / "coin_data.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def coin_app(coin_history_page):
    """Launch the app and require an authenticated Coin History screen."""
    if not coin_history_page.launch_app():
        if coin_history_page.is_login_screen():
            pytest.skip("ABO Tribe is signed out; sign in before running coin tests")
        raise AssertionError("The ABO Tribe app did not open")
    if not coin_history_page.open_history():
        pytest.skip("Coin History is not reachable in the current app build")
    return coin_history_page
