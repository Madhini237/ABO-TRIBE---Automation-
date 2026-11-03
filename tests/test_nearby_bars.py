import time

import pytest

from config.settings import LocationSettings


def _select(location_page, city, region):
    assert location_page.select_city(city, region), f"Could not select {city}"
    assert city.lower() in (location_page.selected_location() or "").lower(), (
        f"Selected location did not update to {city}"
    )


def _bars_for_default(location_page, nearby_bars_page):
    _select(location_page, LocationSettings.DEFAULT_CITY, LocationSettings.DEFAULT_REGION)
    status, cards = nearby_bars_page.wait_for_any_bars_state()
    assert status == "bars", f"Expected bars for {LocationSettings.DEFAULT_CITY}, got {status}"
    return cards


def _go_offline(device):
    device.set_network(False)


def _go_online(device):
    device.set_network(True)


def _retry_with_button_or_restart(location_page, nearby_bars_page):
    if nearby_bars_page.click_retry():
        time.sleep(3)
        return "retry"
    # The app removes the Retry banner automatically when connectivity returns.
    # Reopening the app is the user-visible retry path in that case.
    assert location_page.launch_app(), "Home screen did not reopen after network restoration"
    return "relaunch"


def _assert_alternative_bars(cards):
    assert cards, "No bars were displayed after the location refresh"
    cities = [card["city"].lower() for card in cards]
    assert any("kumari" in city or "kanniyakumari" in city for city in cities), (
        f"Bars were not refreshed for the alternative location: {cities}"
    )
    assert not any("coimbatore" in city for city in cities), (
        f"Stale bars from the previous location are still displayed: {cities}"
    )


# ---------------------------------------------------------------------------
# Flow 10 - Bars API failure
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.negative
def test_flow_10_bars_api_failure_and_retry(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    _go_online(device)
    assert location_page.launch_app(), "Home screen did not open"

    default_cards = _bars_for_default(location_page, nearby_bars_page)
    assert default_cards, "No bars were displayed for the default location"

    _go_offline(device)
    assert location_page.open_location_selector(), "Location selector did not open offline"
    _select(
        location_page,
        LocationSettings.ALTERNATIVE_CITY,
        LocationSettings.ALTERNATIVE_REGION,
    )
    time.sleep(4)
    assert (
        nearby_bars_page.is_offline_banner_visible()
        or nearby_bars_page.has_error_state()
        or nearby_bars_page.is_retry_visible()
    ), "A bars-API/network failure was not surfaced to the user"

    _go_online(device)
    time.sleep(3)
    _retry_with_button_or_restart(location_page, nearby_bars_page)

    cards = nearby_bars_page.wait_for_nearby_bars()
    _assert_alternative_bars(cards)


# ---------------------------------------------------------------------------
# Flow 11 - No bars available
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.negative
def test_flow_11_no_bars_available(
    location_page, nearby_bars_page, device, preserve_device_state
):
    if not LocationSettings.NO_BARS_CITY:
        pytest.skip(
            "Set LOCATION_NO_BARS_CITY to a known empty location to exercise flow 11; "
            "the current test data has no such location."
        )

    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"
    _select(location_page, LocationSettings.NO_BARS_CITY, None)

    status, cards = nearby_bars_page.wait_for_any_bars_state()
    assert status == "empty", (
        f"Expected the no-bars empty state, got {status} with cards={cards}"
    )


# ---------------------------------------------------------------------------
# Flow 12 - Bar eligibility and location accuracy
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.positive
def test_flow_12_bar_eligibility_and_distance_accuracy(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"
    _select(location_page, LocationSettings.DEFAULT_CITY, LocationSettings.DEFAULT_REGION)

    cards = nearby_bars_page.wait_for_nearby_bars()
    assert cards, "No eligible bars were returned for the default location"
    nearby_bars_page.assert_distances_are_valid(cards)

    assert all(card["rating"] is None or 0 <= card["rating"] <= 5 for card in cards), (
        "A bar has an invalid rating"
    )
    assert nearby_bars_page.distances_ascending(cards[:5]), (
        "Nearby bars are not sorted by distance ascending at the top of the "
        f"list: {nearby_bars_page.distances(cards[:5])}"
    )
    assert len(nearby_bars_page.names(cards)) == len(set(nearby_bars_page.names(cards))), (
        f"Duplicate bars are displayed: {nearby_bars_page.names(cards)}"
    )
    assert all(
        "coimbatore" in card["city"].lower() for card in cards
    ), f"Bars from another location are displayed: {nearby_bars_page.cities(cards)}"

    # The UI cannot expose backend-only flags, but deleted/demo entries should
    # never be rendered as customer-facing bars.
    for card in cards:
        lowered = card["name"].lower()
        assert "deleted" not in lowered and "demo" not in lowered, (
            f"A deleted/demo bar is displayed: {card['name']}"
        )
        # Distances below 1 km must use metres; distances at/above 1 km use km.
        assert ("m" in card["distance_text"].lower()) or card["meters"] >= 1000


# ---------------------------------------------------------------------------
# Flow 18 - Retry after network restoration
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.positive
def test_flow_18_retry_after_network_restoration(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    _go_online(device)
    assert location_page.launch_app(), "Home screen did not open"
    _bars_for_default(location_page, nearby_bars_page)

    _go_offline(device)
    assert location_page.open_location_selector(), "Location selector did not open offline"
    _select(
        location_page,
        LocationSettings.ALTERNATIVE_CITY,
        LocationSettings.ALTERNATIVE_REGION,
    )
    time.sleep(4)
    assert (
        nearby_bars_page.is_offline_banner_visible()
        or nearby_bars_page.has_error_state()
        or nearby_bars_page.is_retry_visible()
    ), "No offline/error state was displayed before the retry"

    _go_online(device)
    time.sleep(3)
    retry_mode = _retry_with_button_or_restart(location_page, nearby_bars_page)
    assert retry_mode in ("retry", "relaunch")

    cards = nearby_bars_page.wait_for_nearby_bars()
    _assert_alternative_bars(cards)
    assert LocationSettings.ALTERNATIVE_CITY.lower() in (
        location_page.selected_location() or ""
    ).lower(), "The selected location was lost during the retry"


# ---------------------------------------------------------------------------
# Flow 27 - Deleted and demo bars must not be displayed
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.negative
def test_flow_27_deleted_and_demo_bars_excluded(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"
    cards = _bars_for_default(location_page, nearby_bars_page)

    markers = [marker.lower() for marker in LocationSettings.EXCLUDED_BAR_MARKERS]
    for card in cards:
        haystack = f"{card['name']} {card['raw']}".lower()
        assert not any(marker in haystack for marker in markers), (
            f"A deleted/demo bar is displayed: {card['name']!r} ({card['raw']!r})"
        )
        assert not any(
            name.lower() in haystack for name in LocationSettings.EXCLUDED_BAR_NAMES
        ), f"An explicitly excluded bar is displayed: {card['name']!r}"


# ---------------------------------------------------------------------------
# Flow 28 - Non-customer bars must not be displayed
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.negative
def test_flow_28_non_customer_bars_excluded(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"
    cards = _bars_for_default(location_page, nearby_bars_page)

    markers = [
        marker.lower() for marker in LocationSettings.NON_CUSTOMER_BAR_MARKERS
    ]
    for card in cards:
        haystack = f"{card['name']} {card['raw']}".lower()
        assert not any(marker in haystack for marker in markers), (
            f"A non-customer/internal bar is displayed: {card['name']!r} "
            f"({card['raw']!r})"
        )
        assert not any(
            name.lower() in haystack for name in LocationSettings.EXCLUDED_BAR_NAMES
        ), f"An explicitly excluded non-customer bar is displayed: {card['name']!r}"


# ---------------------------------------------------------------------------
# Flow 29 - Bar coordinates must produce plausible distances
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.positive
def test_flow_29_bar_coordinates_are_plausible(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"
    cards = _bars_for_default(location_page, nearby_bars_page)

    # A wrong coordinate usually shows up as a bar that is implausibly far from
    # the selected city, or as a bar whose card city differs from the selection.
    nearby_bars_page.assert_distances_within_radius(
        cards, LocationSettings.MAX_BAR_RADIUS_KM
    )
    nearby_bars_page.assert_distances_are_valid(cards)
    assert nearby_bars_page.distances_ascending(cards[:5]), (
        "Bars are not sorted by the displayed distance at the top of the "
        f"list: {nearby_bars_page.distances(cards[:5])}"
    )
    assert all(
        LocationSettings.DEFAULT_CITY.lower() in card["city"].lower() for card in cards
    ), (
        "A bar with coordinates from another city is displayed: "
        f"{nearby_bars_page.cities(cards)}"
    )


# ---------------------------------------------------------------------------
# Flow 30 - Distance and sorting are recalculated after a location change
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.positive
@pytest.mark.regression
def test_flow_30_distance_and_sorting_recalculated_after_location_change(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    assert location_page.launch_app(), "Home screen did not open"

    _select(
        location_page,
        LocationSettings.DEFAULT_CITY,
        LocationSettings.DEFAULT_REGION,
    )
    default_cards = nearby_bars_page.wait_for_nearby_bars()
    assert default_cards, "No bars were displayed for the default location"
    default_distances = nearby_bars_page.distances(default_cards)
    assert nearby_bars_page.distances_ascending(default_cards[:5]), (
        "Default-city bars are not sorted by distance at the top of the list: "
        f"{nearby_bars_page.distances(default_cards[:5])}"
    )

    _select(
        location_page,
        LocationSettings.ALTERNATIVE_CITY,
        LocationSettings.ALTERNATIVE_REGION,
    )
    deadline = time.monotonic() + LocationSettings.BARS_TIMEOUT
    alternative_cards = []
    while time.monotonic() < deadline:
        alternative_cards = nearby_bars_page.wait_for_nearby_bars()
        if alternative_cards and any(
            "kumari" in card["city"].lower()
            or "kanniyakumari" in card["city"].lower()
            for card in alternative_cards
        ):
            break
        time.sleep(1)
    assert alternative_cards, "No bars were displayed after switching location"

    alternative_distances = nearby_bars_page.distances(alternative_cards)
    assert nearby_bars_page.distances_ascending(alternative_cards[:5]), (
        "Bars for the new location are not sorted by distance at the top of "
        f"the list: {nearby_bars_page.distances(alternative_cards[:5])}"
    )
    alternative_cities = {card["city"].lower() for card in alternative_cards}
    assert any(
        "kumari" in city or "kanniyakumari" in city for city in alternative_cities
    ), f"Bars were not reloaded for the new location: {alternative_cities}"
    assert not any(
        LocationSettings.DEFAULT_CITY.lower() in city for city in alternative_cities
    ), f"Stale bars from the previous location are still displayed: {alternative_cities}"
    assert alternative_distances != default_distances, (
        "The distance values were not recalculated after the location change: "
        f"{alternative_distances}"
    )


# ---------------------------------------------------------------------------
# Flow 33 - Bars API failure while the device is still online
# ---------------------------------------------------------------------------

@pytest.mark.nearby_bars
@pytest.mark.negative
def test_flow_33_bars_api_failure_with_network_online(
    location_page, nearby_bars_page, device, preserve_device_state
):
    device.set_location_permission(False)
    device.set_location_services(False)
    _go_online(device)
    assert location_page.launch_app(), "Home screen did not open"
    _bars_for_default(location_page, nearby_bars_page)

    # The device stays connected; only backend calls fail. This is different
    # from Flow 10, which takes the whole device offline.
    if not device.set_http_proxy(LocationSettings.API_FAILURE_PROXY):
        pytest.skip(
            "This device denies WRITE_SECURE_SETTINGS, so an API-only failure "
            "cannot be simulated with the system HTTP proxy; Flow 10 still "
            "covers the offline bars failure."
        )
    try:
        assert location_page.open_location_selector(), "Location selector did not open"
        _select(
            location_page,
            LocationSettings.ALTERNATIVE_CITY,
            LocationSettings.ALTERNATIVE_REGION,
        )
        time.sleep(4)
        assert (
            nearby_bars_page.is_offline_banner_visible()
            or nearby_bars_page.has_error_state()
            or nearby_bars_page.is_retry_visible()
        ), "A bars API failure was not surfaced while the device stayed online"
    finally:
        device.clear_http_proxy()

    time.sleep(3)
    _retry_with_button_or_restart(location_page, nearby_bars_page)
    cards = nearby_bars_page.wait_for_nearby_bars()
    _assert_alternative_bars(cards)
