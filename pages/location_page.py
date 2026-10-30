import re
import time

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import LocationSettings
from pages.login_page import LoginPage
from utils.ui_locators import HomeLocators, LocationLocators


class LocationPage:
    """Page object for location detection, selection, search and persistence."""

    def __init__(self, driver, device=None):
        self.driver = driver
        self.device = device
        self.wait = WebDriverWait(driver, LocationSettings.HOME_TIMEOUT)

    # ------------------------------------------------------------- launching
    def launch_app(self, handle_primer="dismiss"):
        """Restart the app and wait for the authenticated home screen.

        handle_primer:
          dismiss - tap "Not right now" on the in-app location primer
          allow   - tap "Allow" (the caller then handles the system dialog)
          leave   - do not touch the primer
        """
        self.driver.terminate_app(LocationSettings.APP_PACKAGE)
        self.driver.execute_script(
            "mobile: startActivity", {"component": LocationSettings.APP_COMPONENT}
        )
        time.sleep(3)

        if handle_primer in ("dismiss", "allow"):
            self._handle_permission_primer(allow=handle_primer == "allow")

        return self.wait_for_home()

    def _handle_permission_primer(self, allow=True):
        try:
            WebDriverWait(self.driver, 6).until(
                EC.presence_of_element_located(LocationLocators.PRIMER_NOT_NOW)
            )
        except TimeoutException:
            return False

        locator = LocationLocators.PRIMER_ALLOW if allow else LocationLocators.PRIMER_NOT_NOW
        element = self.driver.find_elements(*locator)
        if not element:
            return False
        element[0].click()
        time.sleep(2)
        return True

    def _dismiss_primer_if_present(self):
        """Dismiss the in-app location primer if it is covering the screen."""
        if not self.driver.find_elements(*LocationLocators.PRIMER_NOT_NOW):
            return False
        self.driver.find_elements(*LocationLocators.PRIMER_NOT_NOW)[0].click()
        time.sleep(2)
        return True

    def is_login_screen(self):
        return bool(self.driver.find_elements(*LoginPage.MOBILE_NUMBER))

    def wait_for_home(self, timeout=None):
        timeout = timeout or LocationSettings.HOME_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_login_screen():
                return False
            if self._dismiss_primer_if_present():
                continue
            if self.selected_location() and self.driver.find_elements(
                *HomeLocators.SEARCH_BAR
            ):
                return True
            time.sleep(1)
        return False

    def is_home_loaded(self):
        return bool(self.selected_location()) and bool(
            self.driver.find_elements(*HomeLocators.SEARCH_BAR)
        )

    # ------------------------------------------------------------- location
    def selected_location_element(self):
        candidates = []
        for element in self.driver.find_elements(*HomeLocators.LOCATION_HEADER):
            raw = (element.get_attribute("content-desc") or "").strip()
            # The home search bar also contains commas, but it is a single-line
            # label starting with "Search for". Bar cards further down the feed
            # are two-line labels containing a distance bullet. The real header
            # is the only two-line, non-card label in the top 180 px.
            if "\n" not in raw or raw.lower().startswith("search for"):
                continue
            if "•" in raw or "·" in raw:
                continue
            bounds = element.get_attribute("bounds") or ""
            match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
            if not match:
                continue
            top = int(match.group(2))
            if top <= 180:
                candidates.append((top, element))
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item[0])[0][1]

    def selected_location(self):
        element = self.selected_location_element()
        if element is None:
            return None
        return (element.get_attribute("content-desc") or "").strip()

    def selected_city(self):
        text = self.selected_location()
        return text.splitlines()[0].strip() if text else None

    def wait_for_selected_location_change(self, previous, timeout=None):
        timeout = timeout or LocationSettings.GPS_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            current = self.selected_location()
            if current and current != previous:
                return current
            time.sleep(1)
        return self.selected_location()

    def scroll_home_to_top(self):
        for _ in range(12):
            self.dismiss_location_error_dialog()
            if self.selected_location():
                return
            self.driver.execute_script(
                "mobile: scrollGesture",
                {
                    "left": 24, "top": 300, "width": 672, "height": 1000,
                    "direction": "up", "percent": 0.9,
                },
            )
            time.sleep(0.5)
            self.dismiss_location_error_dialog()
        time.sleep(0.5)

    # ------------------------------------------------------------- selector
    def is_selector_open(self):
        return bool(
            self.driver.find_elements(*LocationLocators.ANY_EDIT_TEXT)
            or self.driver.find_elements(*LocationLocators.RECENT_HEADER)
            or self.driver.find_elements(*LocationLocators.SEARCH_RESULTS_HEADER)
            or self.driver.find_elements(*LocationLocators.CURRENT_LOCATION)
            or self.driver.find_elements(*LocationLocators.PERMISSION_BANNER)
        )

    def open_location_selector(self, retries=3):
        if self.is_selector_open():
            return True
        for _ in range(retries):
            self._dismiss_primer_if_present()
            self.scroll_home_to_top()
            header = self.selected_location_element()
            if header is not None:
                try:
                    header.click()
                except (StaleElementReferenceException, Exception):
                    self.driver.tap([(200, 120)])
            else:
                self.driver.tap([(200, 120)])

            if self._wait_for_selector_open(timeout=6):
                return True

            # A mistimed tap can open the Check In screen; recover and retry.
            if self.driver.find_elements(
                "xpath", "//*[contains(@content-desc,'Select a nearby venue')]"
            ):
                self.driver.back()
                time.sleep(2)

        return False

    def _wait_for_selector_open(self, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_selector_open():
                return True
            time.sleep(0.5)
        return False

    def close_location_selector(self):
        self.dismiss_location_error_dialog()
        for _ in range(3):
            if not self.is_selector_open():
                self.wait_for_home()
                return True
            self.driver.back()
            time.sleep(2)
        if not self.is_selector_open():
            self.wait_for_home()
            return True
        return False

    # --------------------------------------------------------------- search
    def search_location(self, query, wait_for_results=True):
        if not self.is_selector_open():
            if not self.open_location_selector():
                raise AssertionError("Location selector did not open")

        field = WebDriverWait(self.driver, LocationSettings.SEARCH_TIMEOUT).until(
            EC.element_to_be_clickable(LocationLocators.ANY_EDIT_TEXT)
        )
        field.click()
        time.sleep(0.5)
        self._clear_search_field(field)
        field.send_keys(query)
        time.sleep(1)

        if wait_for_results:
            self._wait_for_search_feedback()
            deadline = time.monotonic() + LocationSettings.SEARCH_TIMEOUT
            while time.monotonic() < deadline:
                results = self.get_search_results()
                if results:
                    return results
                if self.has_location_not_found() or self.has_network_error():
                    return []
                time.sleep(0.5)
        return self.get_search_results()

    def _clear_search_field(self, field):
        current = (field.get_attribute("text") or field.text or "").strip()
        self.driver.press_keycode(123)  # KEYCODE_MOVE_END
        for _ in range(len(current) + 8):
            self.driver.press_keycode(67)  # KEYCODE_DEL
        time.sleep(0.3)

    def _wait_for_search_feedback(self, timeout=None):
        timeout = timeout or LocationSettings.SEARCH_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.driver.find_elements(*LocationLocators.SEARCH_RESULTS_HEADER):
                return True
            if self.driver.find_elements(*LocationLocators.NOT_FOUND):
                return True
            if self.driver.find_elements(*LocationLocators.NETWORK_ERROR):
                return True
            time.sleep(0.5)
        return False

    def get_search_results(self):
        results = []
        seen = set()
        header_top = None
        headers = self.driver.find_elements(*LocationLocators.SEARCH_RESULTS_HEADER)
        if headers:
            bounds = headers[0].get_attribute("bounds") or ""
            match = re.match(r"\[\d+,(\d+)\]", bounds)
            if match:
                header_top = int(match.group(1))

        for item in self._clickable_labels():
            lines = item["lines"]
            if len(lines) < 2:
                continue
            if header_top is not None and item["top"] is not None and item["top"] < header_top:
                continue
            if item["raw"] in seen:
                continue
            seen.add(item["raw"])
            results.append(
                {
                    "raw": item["raw"],
                    "city": lines[0],
                    "region": lines[1],
                    "element": item["element"],
                    "bounds": item["bounds"],
                }
            )
        return results

    def _clickable_labels(self):
        labels = []
        for element in self.driver.find_elements(
            "xpath", "//*[@clickable='true' and @content-desc!='']"
        ):
            raw = (element.get_attribute("content-desc") or "").strip()
            if not raw:
                continue
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            bounds = element.get_attribute("bounds") or ""
            match = re.match(r"\[\d+,(\d+)\]", bounds)
            labels.append(
                {
                    "raw": raw,
                    "lines": lines,
                    "element": element,
                    "bounds": bounds,
                    "top": int(match.group(1)) if match else None,
                }
            )
        return labels

    def select_search_result(self, city, region=None):
        results = self.get_search_results()
        target = None
        for item in results:
            if item["city"].lower() != city.lower():
                continue
            if region and region.lower() not in item["region"].lower():
                continue
            target = item
            break
        if target is None:
            return False

        target["element"].click()
        time.sleep(3)
        self.wait_for_home()
        return True

    def select_visible_city(self, city, region=None, min_top=0):
        candidates = []
        for element in self.driver.find_elements(
            "xpath", f"//*[@clickable='true' and contains(@content-desc, '{city}')]"
        ):
            raw = (element.get_attribute("content-desc") or "").strip()
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            if not lines or lines[0].lower() != city.lower():
                continue
            if region and (len(lines) < 2 or region.lower() not in lines[1].lower()):
                continue
            bounds = element.get_attribute("bounds") or ""
            match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
            if match and int(match.group(2)) >= min_top:
                candidates.append((int(match.group(2)), element))
        if not candidates:
            return False
        sorted(candidates, key=lambda item: item[0])[0][1].click()
        time.sleep(3)
        self.wait_for_home()
        return True

    def select_city(self, city, region=None):
        """Select a city from recent/other cities, falling back to search."""
        if not self.is_selector_open():
            if not self.open_location_selector():
                raise AssertionError("Location selector did not open")

        if self.select_visible_city(city, region=region):
            return True

        self.search_location(city)
        if self.select_search_result(city, region=region):
            return True
        return False

    def visible_recent_locations(self):
        labels = []
        for item in self._clickable_labels():
            lines = item["lines"]
            if len(lines) >= 2:
                labels.append({"city": lines[0], "region": lines[1], "raw": item["raw"]})
        return labels

    # ------------------------------------------------------ current location
    def current_location_row(self):
        element = None
        rows = self.driver.find_elements(*LocationLocators.CURRENT_LOCATION)
        if rows:
            element = rows[0]
        else:
            # After permission is granted the app replaces the button with the
            # detected address row at the top of the sheet.
            for candidate in self.driver.find_elements(
                "xpath", "//*[@clickable='true' and contains(@content-desc, ',')]"
            ):
                bounds = candidate.get_attribute("bounds") or ""
                match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                if match and 340 <= int(match.group(2)) <= 390:
                    element = candidate
                    break
        return element

    def tap_current_location(self):
        element = self.current_location_row()
        if element is None:
            return False
        element.click()
        time.sleep(3)
        return True

    # ------------------------------------------------------------- feedback
    def has_permission_banner(self):
        return bool(self.driver.find_elements(*LocationLocators.PERMISSION_BANNER))

    def has_location_not_found(self):
        return bool(self.driver.find_elements(*LocationLocators.NOT_FOUND))

    def has_network_error(self):
        return bool(self.driver.find_elements(*LocationLocators.NETWORK_ERROR))

    def has_location_services_prompt(self):
        return bool(self.driver.find_elements(*LocationLocators.LOCATION_SERVICES_PROMPT))

    def has_permission_explanation(self):
        if self.driver.find_elements(*LocationLocators.PERMISSION_EXPLANATION):
            return True
        text = self.driver.page_source.lower()
        phrases = (
            "permission denied",
            "location access is required",
            "allow location access",
            "open settings",
            "enable location access",
            "location permission must",
            "location not detected",
            "access to location services",
            "enable them in settings",
            "go to settings",
        )
        return any(phrase in text for phrase in phrases)

    def has_location_error_dialog(self):
        return bool(
            self.driver.find_elements(*LocationLocators.LOCATION_ERROR_TITLE)
            or self.driver.find_elements(*LocationLocators.GO_TO_SETTINGS)
        )

    def dismiss_location_error_dialog(self):
        if not self.has_location_error_dialog():
            return False
        self.driver.back()
        time.sleep(2)
        return True

    def open_settings_from_error_dialog(self):
        buttons = self.driver.find_elements(*LocationLocators.GO_TO_SETTINGS)
        if not buttons:
            return False
        buttons[0].click()
        time.sleep(3)
        return True

    def request_location_permission(self):
        """Tap the in-sheet permission banner and report whether a dialog opened."""
        if not self.has_permission_banner():
            return False
        self.driver.find_element(*LocationLocators.PERMISSION_BANNER).click()
        time.sleep(2)
        if self.device is not None:
            return self.device.has_system_location_dialog()
        return bool(
            self.driver.find_elements(
                "id", "com.android.permissioncontroller:id/permission_allow_foreground_only_button"
            )
        )

    def retry(self):
        buttons = self.driver.find_elements(*LocationLocators.RETRY)
        if not buttons:
            return False
        buttons[0].click()
        time.sleep(2)
        return True

    def all_visible_labels(self):
        labels = []
        for element in self.driver.find_elements(
            "xpath", "//*[@content-desc!='' or @text!='']"
        ):
            try:
                value = (element.get_attribute("content-desc") or "").strip()
                if value:
                    labels.append(value)
                text = (element.get_attribute("text") or "").strip()
                if text:
                    labels.append(text)
            except StaleElementReferenceException:
                continue
        return labels
