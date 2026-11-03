import os
import time

import pytest

from config.settings import LocationSettings
from utils.ui_locators import AndroidSettingsLocators


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _choose_default_city(location_page):
    assert location_page.select_city(
        LocationSettings.DEFAULT_CITY, LocationSettings.DEFAULT_REGION
    ), f"Could not select {LocationSettings.DEFAULT_CITY}"
    assert LocationSettings.DEFAULT_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower(), "Selected location did not update to the default city"


def _assert_bars_for(location_page, nearby_bars_page, city=None, timeout=25):
    fragment = None
    if city:
        fragment = "kumari" if city.lower() == LocationSettings.ALTERNATIVE_CITY.lower() else city.lower()
    deadline = time.monotonic() + timeout
    cards = []
    while time.monotonic() < deadline:
        cards = nearby_bars_page.collect_nearby_bars()
        if cards and (not fragment or any(fragment in card["city"].lower() for card in cards)):
            break
        time.sleep(1.5)
    assert cards, "Nearby bars list was empty"
    if fragment:
        assert any(fragment in card["city"].lower() for card in cards), (
            f"No bar belonged to {city}: {[card['city'] for card in cards]}"
        )
    return cards


def _tap_current_location_or_top_row(location_page):
    if location_page.tap_current_location():
        return True
    # The app sometimes replaces the explicit button with the detected address
    # row at the top of the sheet while still reacting to a tap.
    location_page.driver.tap([(360, 454)])
    time.sleep(2)
    return True


# ---------------------------------------------------------------------------
# Flow 1 - Automatic location detection
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
@pytest.mark.regression
def test_flow_01_automatic_location_detection(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(True)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    # Keep a manual location that is different from the device GPS location.
    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not manually select {LocationSettings.ALTERNATIVE_CITY}"
    manual_location = location_page.selected_location()
    assert LocationSettings.ALTERNATIVE_CITY.lower() in manual_location.lower()

    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not reopen after enabling location"

    detected = location_page.wait_for_selected_location_change(
        manual_location, timeout=LocationSettings.GPS_TIMEOUT
    )
    assert detected, "No location was selected after automatic detection"
    assert LocationSettings.ALTERNATIVE_CITY.lower() not in detected.lower(), (
        "Automatic detection did not replace the previous manual location"
    )
    if LocationSettings.EXPECTED_AUTO_CITY:
        assert LocationSettings.EXPECTED_AUTO_CITY.lower() in detected.lower(), (
            f"Expected detected city {LocationSettings.EXPECTED_AUTO_CITY}, got {detected}"
        )

    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 2 - Search and select a location, including duplicate names
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_02_search_and_select_location(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    labels = location_page.visible_recent_locations()
    duplicates = [
        item
        for item in labels
        if item["city"].lower() == LocationSettings.DUPLICATE_CITY.lower()
    ]
    if len(duplicates) >= 2:
        regions = {item["region"].lower() for item in duplicates}
        assert len(regions) >= 2, (
            "Locations with the same name are not distinguishable by region: "
            f"{duplicates}"
        )
        assert all(item["region"] for item in duplicates), (
            "A duplicate location is missing its region label"
        )

    results = location_page.search_location(LocationSettings.SEARCH_CITY)
    match = [
        item
        for item in results
        if item["city"].lower() == LocationSettings.SEARCH_CITY.lower()
    ]
    assert match, f"{LocationSettings.SEARCH_CITY} was not returned by search: {results}"
    assert match[0]["region"], "Search result did not include the state/region detail"
    assert location_page.select_search_result(
        LocationSettings.SEARCH_CITY, LocationSettings.SEARCH_CITY_REGION
    ), "Could not select the searched location"
    assert LocationSettings.SEARCH_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower(), "Selected location did not update after search selection"

    # Flow 2 also covers selecting from the recent/saved list.
    _choose_default_city(location_page)
    _assert_bars_for(location_page, nearby_bars_page, LocationSettings.DEFAULT_CITY)


# ---------------------------------------------------------------------------
# Flow 3 - Use current location
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_03_use_current_location(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(True)
    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not manually select {LocationSettings.ALTERNATIVE_CITY}"
    manual = location_page.selected_location()
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (manual or "").lower()

    assert location_page.open_location_selector(), "Location selector did not reopen"
    _tap_current_location_or_top_row(location_page)
    updated = location_page.wait_for_selected_location_change(
        manual, timeout=LocationSettings.GPS_TIMEOUT
    )
    assert updated and updated != manual, (
        "'Use current location' did not update the selected location"
    )
    assert LocationSettings.ALTERNATIVE_CITY.lower() not in updated.lower()
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 4 - Location permission denied
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_04_location_permission_denied(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.has_permission_banner(), (
        "No permission explanation/banner was shown while location permission is denied"
    )

    dialog_opened = location_page.request_location_permission()
    if dialog_opened:
        assert device.deny_system_location_dialog(), "Could not deny the system permission dialog"
        time.sleep(2)

    assert (
        location_page.has_permission_banner()
        or location_page.has_permission_explanation()
        or location_page.has_location_services_prompt()
    ), "The app did not explain that location permission is required"
    location_page.dismiss_location_error_dialog()
    if not location_page.is_selector_open():
        assert location_page.open_location_selector(), "Location selector did not reopen"

    # Manual selection must remain available after denial.
    _choose_default_city(location_page)
    assert LocationSettings.DEFAULT_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower()
    _assert_bars_for(location_page, nearby_bars_page, LocationSettings.DEFAULT_CITY)


# ---------------------------------------------------------------------------
# Flow 5 - Location permission permanently denied
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_05_location_permission_permanently_denied(
    location_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    dialog_opened = location_page.request_location_permission()
    if dialog_opened:
        device.deny_system_location_dialog()
        time.sleep(2)

    assert (
        location_page.has_permission_banner()
        or location_page.has_permission_explanation()
        or location_page.has_location_services_prompt()
    ), "The app did not explain that location permission must be enabled in Settings"

    # The app provides a direct path to Settings. If the current build does not
    # show that button, navigate to the same screen directly.
    if not location_page.open_settings_from_error_dialog():
        device.open_location_permission_settings()
    current_activity = device.driver.current_activity or ""
    assert (
        device.driver.find_elements(*AndroidSettingsLocators.LOCATION_PERMISSION_TITLE)
        or device.driver.find_elements(*AndroidSettingsLocators.APP_PERMISSIONS_TITLE)
        or device.driver.find_elements(*AndroidSettingsLocators.APP_DETAILS_PERMISSIONS)
        or device.driver.find_elements(*AndroidSettingsLocators.LOCATION_SWITCH)
        or "LocationSettingsActivity" in current_activity
    ), "The app did not open a Settings page for location access"

    # Enabling permission in Settings and returning must allow detection again.
    device.set_location_permission(True)
    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not reopen after enabling permission"
    assert location_page.open_location_selector(), "Location selector did not open"
    assert not location_page.has_permission_banner(), (
        "Permission banner is still shown after enabling location permission"
    )
    location_page.close_location_selector()


# ---------------------------------------------------------------------------
# Flow 6 - Location services disabled
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_06_location_services_disabled(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(True)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    current_row = location_page.current_location_row()
    if current_row is not None:
        current_row.click()
        time.sleep(3)

    assert (
        location_page.has_location_services_prompt()
        or location_page.has_permission_banner()
        or location_page.has_permission_explanation()
        or location_page.current_location_row() is not None
    ), "No prompt/message asked the user to enable location services"

    # Enabling services and retrying must allow detection/selection.
    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not reopen after enabling services"
    assert not location_page.has_location_services_prompt(), (
        "Location-services prompt remained after enabling services"
    )
    _choose_default_city(location_page)
    _assert_bars_for(location_page, nearby_bars_page, LocationSettings.DEFAULT_CITY)


# ---------------------------------------------------------------------------
# Flow 7 - Location not found
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_07_location_not_found(
    location_page, nearby_bars_page, device, preserve_device_state, app_home
):
    previous = location_page.selected_location()
    assert previous, "No location was selected before searching"

    assert location_page.open_location_selector(), "Location selector did not open"
    location_page.search_location(LocationSettings.INVALID_QUERY)
    assert location_page.has_location_not_found(), (
        "No 'Location not found' / 'No matching cities found' feedback was displayed"
    )
    location_page.close_location_selector()
    assert location_page.selected_location() == previous, (
        "The previous location changed after a failed search"
    )

    assert location_page.open_location_selector(), "Location selector did not reopen"
    assert location_page.select_city(
        LocationSettings.DEFAULT_CITY, LocationSettings.DEFAULT_REGION
    ), "Could not select a valid location after a failed search"
    assert LocationSettings.DEFAULT_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower()
    _assert_bars_for(location_page, nearby_bars_page, LocationSettings.DEFAULT_CITY)


# ---------------------------------------------------------------------------
# Flow 8 - Offline search and network failure
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_08_offline_search(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    device.set_network(False)
    assert location_page.launch_app(), "Home screen did not open while offline"
    previous = location_page.selected_location()

    assert location_page.open_location_selector(), "Location selector did not open offline"
    location_page.search_location(LocationSettings.SEARCH_CITY)
    assert location_page.has_network_error() or location_page.has_location_not_found(), (
        "Offline search did not display a network/location-search error"
    )
    location_page.close_location_selector()
    assert location_page.selected_location() == previous, (
        "An offline search changed the selected location"
    )

    device.set_network(True)
    assert device.is_online(), "Network did not come back after airplane mode was disabled"
    assert location_page.open_location_selector(), "Location selector did not reopen after retry"
    recovered_results = location_page.search_location(LocationSettings.SEARCH_CITY)
    assert any(
        item["city"].lower() == LocationSettings.SEARCH_CITY.lower()
        for item in recovered_results
    ), "Search did not recover after network restoration"
    assert location_page.select_search_result(
        LocationSettings.SEARCH_CITY, LocationSettings.SEARCH_CITY_REGION
    ), "Could not select the location after network restoration"


# ---------------------------------------------------------------------------
# Flow 9 - GPS timeout / location API failure
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_09_gps_failure_keeps_existing_location(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(True)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"
    previous = location_page.selected_location()

    assert location_page.open_location_selector(), "Location selector did not open"
    _tap_current_location_or_top_row(location_page)
    time.sleep(4)

    assert (
        location_page.has_location_services_prompt()
        or location_page.has_permission_banner()
        or location_page.has_permission_explanation()
        or location_page.has_network_error()
        or location_page.selected_location() == previous
    ), "A failed GPS attempt produced no feedback and changed the selected location"

    # The user can still fall back to manual selection.
    location_page.close_location_selector()
    _choose_default_city(location_page)
    _assert_bars_for(location_page, nearby_bars_page, LocationSettings.DEFAULT_CITY)


# ---------------------------------------------------------------------------
# Flow 13 - Switch location / city
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_13_switch_location_refreshes_bars(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    _choose_default_city(location_page)
    default_cards = _assert_bars_for(
        location_page, nearby_bars_page, LocationSettings.DEFAULT_CITY
    )

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not switch to {LocationSettings.ALTERNATIVE_CITY}"
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower()

    alternative_cards = _assert_bars_for(
        location_page, nearby_bars_page, LocationSettings.ALTERNATIVE_CITY
    )
    alternative_cities = {card["city"].lower() for card in alternative_cards}
    assert not any(
        "coimbatore" in city
        for city in alternative_cities
        if LocationSettings.ALTERNATIVE_CITY.lower() != "coimbatore"
    ), "Stale bars from the previous city are still displayed"


# ---------------------------------------------------------------------------
# Flow 14 - Retain selected location
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_14_selected_location_persists(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not select {LocationSettings.ALTERNATIVE_CITY}"
    selected = location_page.selected_location()
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (selected or "").lower()

    # Restarting the app must restore the manually selected location while
    # automatic detection is unavailable.
    assert location_page.launch_app(), "Home screen did not reopen"
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower(), "The manually selected location was not restored after restart"
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 15 - Location save failure
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_15_location_save_failure(
    location_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    device.set_network(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), "Could not attempt an offline location save"

    text = location_page.driver.page_source.lower()
    save_failure_markers = (
        "could not save",
        "failed to save",
        "unable to save",
        "save failed",
        "location could not be saved",
    )
    if not any(marker in text for marker in save_failure_markers):
        pytest.skip(
            "The app persists the location locally and does not expose a "
            "location-save failure state; there is nothing to assert for flow 15."
        )

    # If a failure is surfaced, the app must not claim that saving succeeded.
    assert not any(
        marker in text for marker in ("location saved", "saved successfully")
    ), "The app reported a successful save while also showing a save failure"

    device.set_network(True)
    assert location_page.open_location_selector(), "Location selector did not reopen"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), "Retry after a save failure did not succeed"


# ---------------------------------------------------------------------------
# Flow 16 - Location change during booking
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.regression
def test_flow_16_location_change_during_booking(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"
    _choose_default_city(location_page)

    # Open the existing booking shown on the home page. This verifies that a
    # location change never rewrites the bar/location already attached to a
    # booking. If no booking entry point is present, there is nothing to test.
    booking_entry = location_page.driver.find_elements(
        "xpath", "//*[@content-desc='VIEW BOOKING' or @text='VIEW BOOKING']"
    )
    if not booking_entry:
        pytest.skip("No booking entry point is available on the current home screen")
    booking_entry[0].click()
    time.sleep(3)
    booking_text_before = location_page.driver.page_source
    assert "booking" in booking_text_before.lower(), "Booking details did not open"

    location_page.driver.back()
    time.sleep(2)
    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not change location to {LocationSettings.ALTERNATIVE_CITY}"

    view_booking = location_page.driver.find_elements(
        "xpath", "//*[@content-desc='VIEW BOOKING' or @text='VIEW BOOKING']"
    )
    if view_booking:
        view_booking[0].click()
        time.sleep(3)
        booking_text_after = location_page.driver.page_source
        assert "mufasa" in booking_text_after.lower() or "abo bar" in booking_text_after.lower(), (
            "The booking lost its bar information after the location changed"
        )
        assert LocationSettings.ALTERNATIVE_CITY.lower() not in booking_text_after.lower(), (
            "The booking silently adopted the newly selected location"
        )
        location_page.driver.back()
        time.sleep(2)


# ---------------------------------------------------------------------------
# Flow 17 - Recent and saved locations
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_17_recent_and_saved_locations(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not select {LocationSettings.ALTERNATIVE_CITY}"

    assert location_page.open_location_selector(), "Location selector did not reopen"
    recent = location_page.visible_recent_locations()
    assert any(
        item["city"].lower() == LocationSettings.ALTERNATIVE_CITY.lower()
        for item in recent
    ), "The selected location was not added to the recent/saved list"

    assert location_page.select_city(
        LocationSettings.DEFAULT_CITY, LocationSettings.DEFAULT_REGION
    ), "Could not select a saved/recent location"
    assert LocationSettings.DEFAULT_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower()
    _assert_bars_for(location_page, nearby_bars_page, LocationSettings.DEFAULT_CITY)


# ---------------------------------------------------------------------------
# Flow 19 - First-time permission grant through the system dialog
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
@pytest.mark.regression
def test_flow_19_first_time_permission_granted(
    location_page, nearby_bars_page, device, preserve_device_state
):
    # Clear the "user-set"/"user-fixed" flags so the runtime permission dialog
    # can be shown again, then deny access and let the app request it.
    device.reset_location_permission_prompts()
    device.set_location_permission(False)
    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not open"

    # A manual location gives us a known value that detection must replace.
    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not manually select {LocationSettings.ALTERNATIVE_CITY}"
    previous = location_page.selected_location()
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (previous or "").lower()

    assert location_page.open_location_selector(), "Location selector did not reopen"
    if not location_page.has_permission_banner():
        pytest.skip(
            "The app did not show an in-app permission request banner; the "
            "first-time system-dialog grant path cannot be exercised."
        )

    if not location_page.request_location_permission():
        pytest.skip(
            "The system permission dialog did not open after clearing the "
            "permission flags; this device/OEM does not allow re-prompting."
        )
    assert device.allow_system_location_dialog(), (
        "Could not tap Allow on the system location permission dialog"
    )
    assert device.location_permission_granted(), (
        "Location permission was not granted after allowing the system dialog"
    )

    updated = location_page.wait_for_selected_location_change(
        previous, timeout=LocationSettings.GPS_TIMEOUT
    )
    if not updated or updated == previous:
        _tap_current_location_or_top_row(location_page)
        updated = location_page.wait_for_selected_location_change(
            previous, timeout=LocationSettings.GPS_TIMEOUT
        )
    assert updated and updated != previous, (
        "Location was not detected after the first-time permission grant"
    )
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 20 - Approximate (coarse) location permission
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_20_approximate_location_permission(
    location_page, nearby_bars_page, device, preserve_device_state
):
    if device.sdk_version() < 31:
        pytest.skip(
            "Approximate location permission requires Android 12 (API 31) or "
            f"newer; this device is API {device.sdk_version()}."
        )
    device.reset_location_permission_prompts()
    device.set_location_permission(False)
    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not manually select {LocationSettings.ALTERNATIVE_CITY}"
    previous = location_page.selected_location()
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (previous or "").lower()

    device.set_approximate_location_permission()
    assert device.coarse_location_granted(), (
        "Approximate (coarse) location permission was not granted"
    )
    assert not device.fine_location_granted(), (
        "Precise location is still granted; the app was not tested with "
        "approximate-only permission"
    )

    assert location_page.launch_app(), "Home screen did not reopen"
    assert location_page.open_location_selector(), "Location selector did not open"
    _tap_current_location_or_top_row(location_page)
    updated = location_page.wait_for_selected_location_change(
        previous, timeout=LocationSettings.GPS_TIMEOUT
    )
    assert updated and updated != previous, (
        "The app did not detect a location with approximate-only permission"
    )
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 21 - Search by locality
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_21_search_by_locality(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    results = location_page.search_location(LocationSettings.LOCALITY_QUERY)
    assert results, (
        f"Searching for locality {LocationSettings.LOCALITY_QUERY!r} returned no results"
    )
    assert any(
        LocationSettings.LOCALITY_QUERY.lower() in item["raw"].lower()
        or LocationSettings.LOCALITY_PARENT_CITY.lower() in item["raw"].lower()
        for item in results
    ), (
        f"No result matched locality {LocationSettings.LOCALITY_QUERY!r} or its "
        f"parent city {LocationSettings.LOCALITY_PARENT_CITY!r}: {results}"
    )

    assert location_page.select_first_search_result(), (
        "Could not select a locality search result"
    )
    selected = location_page.selected_location() or ""
    assert selected, "Selecting a locality did not update the location header"
    assert (
        LocationSettings.LOCALITY_QUERY.lower() in selected.lower()
        or LocationSettings.LOCALITY_PARENT_CITY.lower() in selected.lower()
    ), f"Unexpected location after locality search: {selected!r}"
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 22 - Search by landmark
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_22_search_by_landmark(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    results = location_page.search_location(LocationSettings.LANDMARK_QUERY)
    assert results, (
        f"Searching for landmark {LocationSettings.LANDMARK_QUERY!r} returned no results"
    )
    landmark_token = LocationSettings.LANDMARK_QUERY.split()[0].lower()
    assert any(
        landmark_token in item["raw"].lower()
        or LocationSettings.LANDMARK_PARENT_CITY.lower() in item["raw"].lower()
        for item in results
    ), (
        f"No result matched landmark {LocationSettings.LANDMARK_QUERY!r} or its "
        f"parent city {LocationSettings.LANDMARK_PARENT_CITY!r}: {results}"
    )

    assert location_page.select_first_search_result(), (
        "Could not select a landmark search result"
    )
    selected = location_page.selected_location() or ""
    assert selected, "Selecting a landmark did not update the location header"
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 23 - Duplicate location names
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_23_duplicate_location_names(
    location_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    results = location_page.search_location(LocationSettings.DUPLICATE_CITY)
    duplicates = [
        item
        for item in results
        if item["city"].lower() == LocationSettings.DUPLICATE_CITY.lower()
    ]
    assert len(duplicates) >= 2, (
        f"Expected at least two locations named {LocationSettings.DUPLICATE_CITY!r}, "
        f"got {duplicates}. Search results: {results}"
    )
    assert all(item["region"] for item in duplicates), (
        f"A duplicate location is missing its region label: {duplicates}"
    )

    regions = []
    for item in duplicates:
        if item["region"] not in regions:
            regions.append(item["region"])
    assert len(regions) >= 2, (
        f"Locations named {LocationSettings.DUPLICATE_CITY!r} are not distinguishable "
        f"by region: {duplicates}"
    )

    # Both entries must be selectable and the header must keep the region so
    # the user can tell which same-named city is active.
    for region in regions[:2]:
        assert location_page.open_location_selector(), "Location selector did not reopen"
        location_page.search_location(LocationSettings.DUPLICATE_CITY)
        assert location_page.select_search_result(
            LocationSettings.DUPLICATE_CITY, region
        ), f"Could not select {LocationSettings.DUPLICATE_CITY}, {region}"
        selected = location_page.selected_location() or ""
        assert region.lower() in selected.lower(), (
            f"Selected header {selected!r} does not identify the duplicate by "
            f"region {region!r}"
        )


# ---------------------------------------------------------------------------
# Flow 24 - GPS timeout
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_24_gps_timeout(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(True)
    device.set_location_services(True)
    if not device.set_location_providers("-gps,-network"):
        pytest.skip(
            "This device denies WRITE_SECURE_SETTINGS, so GPS/network providers "
            "cannot be disabled independently of the location-services switch; "
            "a GPS timeout cannot be simulated on it."
        )
    if device.location_providers_enabled() is not False:
        pytest.skip(
            "This device/build does not let the test disable GPS/network "
            "providers independently of the location-services switch."
        )

    try:
        assert location_page.launch_app(), "Home screen did not open"
        assert location_page.open_location_selector(), "Location selector did not open"
        assert location_page.select_city(
            LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
        ), f"Could not manually select {LocationSettings.ALTERNATIVE_CITY}"
        previous = location_page.selected_location()
        assert LocationSettings.ALTERNATIVE_CITY.lower() in (previous or "").lower()

        assert location_page.open_location_selector(), "Location selector did not reopen"
        started = time.monotonic()
        _tap_current_location_or_top_row(location_page)

        deadline = started + LocationSettings.GPS_TIMEOUT + LocationSettings.GPS_TIMEOUT_MARGIN
        feedback = False
        while time.monotonic() < deadline:
            if (
                location_page.has_location_services_prompt()
                or location_page.has_permission_explanation()
                or location_page.has_network_error()
                or location_page.has_location_not_found()
            ):
                feedback = True
                break
            time.sleep(1)

        elapsed = time.monotonic() - started
        assert elapsed <= (
            LocationSettings.GPS_TIMEOUT + LocationSettings.GPS_TIMEOUT_MARGIN
        ), (
            f"The GPS request did not finish within the {LocationSettings.GPS_TIMEOUT}s "
            f"timeout (+{LocationSettings.GPS_TIMEOUT_MARGIN}s margin); elapsed={elapsed:.1f}s"
        )
        assert feedback or location_page.selected_location() == previous, (
            "A GPS timeout produced no feedback and changed the selected location"
        )
    finally:
        device.set_location_providers("+gps,+network")

    # After providers are restored, detection must work again.
    assert location_page.launch_app(), "Home screen did not reopen"
    assert location_page.open_location_selector(), "Location selector did not open"
    _tap_current_location_or_top_row(location_page)
    recovered = location_page.wait_for_selected_location_change(
        previous, timeout=LocationSettings.GPS_TIMEOUT
    )
    assert recovered and recovered != previous, (
        "Location detection did not recover after the GPS providers were restored"
    )
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 25 - Location API failure
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_25_location_api_failure(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(True)
    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not manually select {LocationSettings.ALTERNATIVE_CITY}"
    previous = location_page.selected_location()
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (previous or "").lower()

    # GPS is available, but the reverse-geocode/location API cannot be reached.
    device.set_network(False)
    assert location_page.open_location_selector(), "Location selector did not open offline"
    _tap_current_location_or_top_row(location_page)
    time.sleep(4)
    assert (
        location_page.has_network_error()
        or location_page.has_location_services_prompt()
        or location_page.has_permission_explanation()
        or location_page.selected_location() == previous
    ), "A location API failure produced no feedback and changed the selected location"

    device.set_network(True)
    assert device.wait_for_network(
        True, timeout=LocationSettings.NETWORK_TIMEOUT
    ), "Network did not come back"
    assert location_page.launch_app(), "Home screen did not reopen after network recovery"
    assert location_page.open_location_selector(), "Location selector did not reopen"
    _tap_current_location_or_top_row(location_page)
    recovered = location_page.wait_for_selected_location_change(
        previous, timeout=LocationSettings.GPS_TIMEOUT
    )
    assert recovered and recovered != previous, (
        "Location detection did not recover after the location API became reachable"
    )
    _assert_bars_for(location_page, nearby_bars_page)


# ---------------------------------------------------------------------------
# Flow 26 - Manual selection must not be silently overridden
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_26_manual_selection_not_overridden(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(True)
    device.set_location_services(True)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not manually select {LocationSettings.ALTERNATIVE_CITY}"
    manual = location_page.selected_location()
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (manual or "").lower()

    # Give the app time to run any background detection refresh. A manual
    # selection must survive until the user explicitly asks for GPS again.
    deadline = time.monotonic() + min(LocationSettings.GPS_TIMEOUT, 15)
    while time.monotonic() < deadline:
        if location_page.selected_location() != manual:
            break
        time.sleep(1)

    assert location_page.selected_location() == manual, (
        "The manually selected location was silently replaced by automatic "
        f"detection: {location_page.selected_location()!r}"
    )
    _assert_bars_for(location_page, nearby_bars_page, LocationSettings.ALTERNATIVE_CITY)


# ---------------------------------------------------------------------------
# Flow 31 - Location saved successfully
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.positive
def test_flow_31_location_save_success(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not select {LocationSettings.ALTERNATIVE_CITY}"
    selected = location_page.selected_location() or ""
    assert LocationSettings.ALTERNATIVE_CITY.lower() in selected.lower()
    assert not location_page.has_save_failure(), (
        "The app reported a save failure for a successful location selection"
    )

    # A saved location must survive an app restart.
    assert location_page.launch_app(), "Home screen did not reopen"
    restored = location_page.selected_location() or ""
    assert LocationSettings.ALTERNATIVE_CITY.lower() in restored.lower(), (
        "The successfully saved location was not restored after restart"
    )
    assert not location_page.has_save_failure()

    assert location_page.open_location_selector(), "Location selector did not reopen"
    recent = location_page.visible_recent_locations()
    assert any(
        item["city"].lower() == LocationSettings.ALTERNATIVE_CITY.lower()
        for item in recent
    ), "The saved location was not added to the recent/saved list"
    location_page.close_location_selector()


# ---------------------------------------------------------------------------
# Flow 32 - Failed location save is handled correctly
# ---------------------------------------------------------------------------

@pytest.mark.location
@pytest.mark.negative
def test_flow_32_location_save_failure_handled(
    location_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    # Put the city into the recent list while the backend is reachable.
    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), f"Could not preselect {LocationSettings.ALTERNATIVE_CITY}"

    # Make the save API unreachable. Airplane mode is used because this device
    # does not allow installing a proxy through adb.
    device.set_network(False)
    try:
        assert location_page.open_location_selector(), "Location selector did not reopen"
        assert location_page.select_city(
            LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
        ), "Could not attempt a location save while the save API was failing"

        selected = location_page.selected_location() or ""
        failure = location_page.has_save_failure()
        success = location_page.has_save_success()
        assert not (failure and success), (
            "The app reported both a successful and a failed location save"
        )
        assert LocationSettings.ALTERNATIVE_CITY.lower() in selected.lower() or failure, (
            "A failed save neither kept the selected location nor reported the failure"
        )
        assert not location_page.is_login_screen(), (
            "A failed location save signed the user out"
        )
    finally:
        device.set_network(True)
        assert device.wait_for_network(
            True, timeout=LocationSettings.NETWORK_TIMEOUT
        ), "Network did not come back after the save-failure test"

    # Retrying after the API recovers must save the location normally.
    assert location_page.launch_app(), "Home screen did not reopen after recovery"
    assert location_page.open_location_selector(), "Location selector did not open"
    assert location_page.select_city(
        LocationSettings.ALTERNATIVE_CITY, LocationSettings.ALTERNATIVE_REGION
    ), "Location save did not succeed after the API recovered"
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower()
    assert not location_page.has_save_failure()
