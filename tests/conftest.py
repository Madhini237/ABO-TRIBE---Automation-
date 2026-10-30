import pytest

from appium import webdriver
from appium.options.android import UiAutomator2Options

from pages.location_page import LocationPage
from pages.nearby_bars_page import NearbyBarsPage
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
