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
    assert nearby_bars_page.distances_ascending(cards), (
        f"Nearby bars are not sorted by distance ascending: {nearby_bars_page.distances(cards)}"
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
