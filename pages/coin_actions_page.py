"""Actions that earn or spend coins in the ABO Tribe bar flows.

The coin history feature is only useful if the credits and deductions are
created through the real user journeys. This page object keeps the navigation
generic (labels are read from the accessibility tree) so the coin tests can
exercise Skip the Queue, Song Request, Shoutout, Games, check-in and profile
completion without duplicating a page object for every bar screen.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import CoinSettings
from pages.login_page import LoginPage
from utils import coin_parser
from utils.ui_locators import (
    CoinActionLocators,
    CoinLocators,
    HomeLocators,
    LocationLocators,
    NearbyBarsLocators,
)


@dataclass
class CoinActionResult:
    action: str
    attempted: bool
    status: str
    message: str = ""
    detail: dict = field(default_factory=dict)

    @property
    def succeeded(self):
        return self.status in ("success", "accepted", "won", "already_checked_in")

    @property
    def blocked(self):
        return self.status in (
            "insufficient_coins",
            "not_checked_in",
            "feature_unavailable",
            "login_required",
        )


class CoinActionsPage:
    """Drives the user journeys that generate coin credits and deductions."""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, CoinSettings.TIMEOUT)

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _label(element):
        try:
            content = (element.get_attribute("content-desc") or "").strip()
            text = (element.get_attribute("text") or "").strip()
        except (StaleElementReferenceException, WebDriverException):
            return ""
        values = []
        for value in (content, text):
            if value and value not in values:
                values.append(value)
        return "\n".join(values).strip()

    def _visible(self, locator):
        try:
            return bool(self.driver.find_elements(*locator))
        except WebDriverException:
            return False

    def _find_clickable(self, locator):
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except (StaleElementReferenceException, WebDriverException):
                continue
        return None

    def _click(self, locator, timeout=None):
        try:
            element = WebDriverWait(
                self.driver, timeout or CoinSettings.TIMEOUT
            ).until(EC.element_to_be_clickable(locator))
            element.click()
            time.sleep(1)
            return True
        except (TimeoutException, StaleElementReferenceException, WebDriverException):
            return False

    def page_text(self):
        try:
            return (self.driver.page_source or "").lower()
        except WebDriverException:
            return ""

    def _screen_size(self):
        try:
            size = self.driver.get_window_size()
            return int(size.get("width", 720)), int(size.get("height", 1280))
        except WebDriverException:
            return 720, 1280

    def is_login_screen(self):
        return bool(self.driver.find_elements(*LoginPage.MOBILE_NUMBER))

    def _dismiss_dialogs(self):
        for locator in (
            LocationLocators.PRIMER_NOT_NOW,
            CoinLocators.CANCEL,
            ("xpath", "//*[contains(@content-desc,'Not right now')]"),
        ):
            elements = self.driver.find_elements(*locator)
            for element in elements:
                try:
                    if element.is_displayed():
                        element.click()
                        time.sleep(1)
                        return True
                except (StaleElementReferenceException, WebDriverException):
                    continue
        return False

    # ------------------------------------------------------------- lifecycle
    def launch_home(self):
        self.driver.terminate_app(CoinSettings.APP_PACKAGE)
        self.driver.execute_script(
            "mobile: startActivity", {"component": CoinSettings.APP_COMPONENT}
        )
        time.sleep(3)
        self._dismiss_dialogs()
        deadline = time.monotonic() + CoinSettings.OPEN_TIMEOUT
        while time.monotonic() < deadline:
            if self.is_login_screen():
                return False
            if self.is_home_loaded() or self.driver.find_elements(*HomeLocators.SEARCH_BAR):
                return True
            self._dismiss_dialogs()
            time.sleep(0.5)
        return self.driver.current_package == CoinSettings.APP_PACKAGE

    def is_home_loaded(self):
        return bool(
            self.driver.find_elements(*NearbyBarsLocators.BAR_CARD)
            or self.driver.find_elements(*HomeLocators.SEARCH_BAR)
            or self.driver.find_elements(*CoinLocators.COINS_ENTRY)
        )

    def go_home(self):
        for locator in (
            ("accessibility id", "Home"),
            CoinActionLocators.HOME_TAB,
        ):
            element = self._find_clickable(locator)
            if element is not None:
                try:
                    element.click()
                    time.sleep(2)
                    return True
                except (StaleElementReferenceException, WebDriverException):
                    continue
        for _ in range(3):
            try:
                self.driver.back()
                time.sleep(1)
                if self.is_home_loaded():
                    return True
            except WebDriverException:
                break
        return self.launch_home()

    def scroll_home(self, direction="down", percent=0.75):
        try:
            self.driver.execute_script(
                "mobile: scrollGesture",
                {
                    "left": 24,
                    "top": 260,
                    "width": 672,
                    "height": 1000,
                    "direction": direction,
                    "percent": percent,
                },
            )
            time.sleep(0.7)
        except WebDriverException:
            pass

    # ----------------------------------------------------------------- bars
    def open_bar(self, bar_name=None):
        """Open a bar's detail screen (the location of the coin features)."""
        if self.is_login_screen():
            return False
        if not self.driver.find_elements(*NearbyBarsLocators.BAR_CARD):
            self.go_home()

        bar_name = bar_name or CoinSettings.BAR_NAME
        for attempt in range(4):
            cards = self.driver.find_elements(*NearbyBarsLocators.BAR_CARD)
            target = None
            for card in cards:
                label = self._label(card)
                if not label or "•" not in label:
                    continue
                if not bar_name or bar_name.lower() in label.lower():
                    target = card
                    break
            if target is not None:
                try:
                    target.click()
                    time.sleep(2)
                    if self._on_bar_detail() or self._visible(
                        CoinActionLocators.CHECK_IN_BUTTON
                    ):
                        return True
                    # A card can open a nested page (offers/events); recover.
                    self.driver.back()
                    time.sleep(1)
                except (StaleElementReferenceException, WebDriverException):
                    pass
            self.scroll_home()
            if attempt == 1:
                self.go_home()
        return False

    def _on_bar_detail(self):
        text = self.page_text()
        return any(
            marker in text
            for marker in (
                "check in",
                "check-in",
                "skip the queue",
                "song request",
                "shoutout",
                "shout out",
                "game",
                "about",
                "menu",
            )
        )

    def is_checked_in(self):
        text = self.page_text()
        if any(marker in text for marker in CoinSettings.NOT_CHECKED_IN_MARKERS):
            return False
        return any(marker in text for marker in CoinSettings.CHECKED_IN_MARKERS)

    # -------------------------------------------------------------- check-in
    def check_in(self, bar_name=None):
        if self.is_login_screen():
            return CoinActionResult("check_in", False, "login_required")
        if self.is_checked_in():
            return CoinActionResult("check_in", True, "already_checked_in")

        if not self.open_bar(bar_name):
            return CoinActionResult("check_in", False, "not_found", "Bar detail did not open")

        button = self._find_clickable(CoinActionLocators.CHECK_IN_BUTTON)
        if button is None:
            return CoinActionResult("check_in", False, "not_found", "Check-in control was not found")
        try:
            button.click()
            time.sleep(2)
        except (StaleElementReferenceException, WebDriverException) as error:
            return CoinActionResult("check_in", False, "error", str(error))

        self._confirm_if_needed()
        status = self._wait_for_check_in_status()
        return CoinActionResult(
            "check_in",
            True,
            status,
            message=self._feedback_message(),
        )

    def _confirm_if_needed(self):
        for locator in (CoinLocators.CONFIRM, CoinActionLocators.SUBMIT):
            element = self._find_clickable(locator)
            if element is not None:
                try:
                    element.click()
                    time.sleep(1)
                    return True
                except (StaleElementReferenceException, WebDriverException):
                    continue
        return False

    def _wait_for_check_in_status(self, timeout=None):
        timeout = timeout or CoinSettings.FEEDBACK_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._visible(CoinActionLocators.CHECK_IN_REJECTED):
                return "rejected"
            if self._visible(CoinActionLocators.CHECK_IN_PENDING):
                return "pending"
            if (
                self._visible(CoinActionLocators.CHECK_IN_SUCCESS)
                or self.is_checked_in()
            ):
                return "accepted"
            # The check-in button disappearing is a successful acceptance in
            # auto-approval builds.
            if not self._visible(CoinActionLocators.CHECK_IN_BUTTON):
                if not self.has_blocking_message():
                    return "accepted"
            time.sleep(0.5)
        return "error"

    # ------------------------------------------------------------- features
    def _feature_locator(self, feature):
        mapping = {
            "skip": CoinActionLocators.SKIP_THE_QUEUE,
            "skip_the_queue": CoinActionLocators.SKIP_THE_QUEUE,
            "song": CoinActionLocators.SONG_REQUEST,
            "song_request": CoinActionLocators.SONG_REQUEST,
            "shoutout": CoinActionLocators.SHOUTOUT_REQUEST,
            "shoutout_request": CoinActionLocators.SHOUTOUT_REQUEST,
            "game": CoinActionLocators.GAME,
            "game_entry": CoinActionLocators.GAME_ENTRY,
        }
        return mapping.get(feature, CoinActionLocators.GAME)

    def open_feature(self, feature, bar_name=None):
        """Open a feature screen/dialog and classify the visible feedback."""
        if self.is_login_screen():
            return CoinActionResult(feature, False, "login_required")
        if not self.open_bar(bar_name):
            return CoinActionResult(feature, False, "not_found", "Bar detail did not open")

        locator = self._feature_locator(feature)
        elements = self.driver.find_elements(*locator)
        if not elements:
            self.scroll_home()
            elements = self.driver.find_elements(*locator)
        if not elements and str(feature).startswith("game"):
            elements = self.driver.find_elements(*CoinActionLocators.GAME)
        if not elements:
            return CoinActionResult(
                feature, False, "feature_unavailable", "Feature entry was not present"
            )

        clicked = False
        for element in elements:
            try:
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    time.sleep(2)
                    clicked = True
                    break
            except (StaleElementReferenceException, WebDriverException):
                continue
        if not clicked:
            return CoinActionResult(feature, False, "error", "Feature could not be opened")

        self._confirm_if_needed()
        status = self._wait_for_feedback()
        return CoinActionResult(feature, True, status, self._feedback_message())

    # ------------------------------------------------------------- spending
    def trigger_skip_the_queue(self, bar_name=None):
        result = self.open_feature("skip_the_queue", bar_name=bar_name)
        if result.status in ("success", "not_found"):
            result.status = self._wait_for_feedback()
        result.action = "skip_the_queue"
        return result

    def submit_song_request(self, song_name=None, bar_name=None):
        result = self.open_feature("song_request", bar_name=bar_name)
        if result.blocked or not result.attempted:
            result.action = "song_request"
            return result
        self._fill_first_input(song_name or CoinSettings.SONG_NAME)
        self._submit_form()
        result.status = self._wait_for_feedback()
        result.message = self._feedback_message()
        result.action = "song_request"
        return result

    def send_shoutout(self, message=None, bar_name=None):
        result = self.open_feature("shoutout_request", bar_name=bar_name)
        if result.blocked or not result.attempted:
            result.action = "shoutout_request"
            return result
        self._fill_first_input(message or CoinSettings.SHOUTOUT_MESSAGE)
        self._submit_form()
        result.status = self._wait_for_feedback()
        result.message = self._feedback_message()
        result.action = "shoutout_request"
        return result

    def start_game(self, game_name=None, bar_name=None):
        result = self.open_feature("game_entry", bar_name=bar_name)
        if result.blocked or not result.attempted:
            result.action = "game_entry"
            return result

        # A game list may need an explicit game/play tap.
        if game_name:
            clicked = self._click_text(game_name)
            if clicked:
                time.sleep(2)
        for locator in (CoinActionLocators.GAME_ENTRY, CoinActionLocators.GAME_PLAY):
            element = self._find_clickable(locator)
            if element is not None:
                try:
                    element.click()
                    time.sleep(2)
                    break
                except (StaleElementReferenceException, WebDriverException):
                    continue

        result.status = self._wait_for_feedback(extra_markers=("you won", "you win", "you lost", "better luck"))
        result.message = self._feedback_message()
        result.action = "game_entry"
        return result

    def play_until_win(self, attempts=None):
        """Try the game until a win is observed or the attempts run out.

        Returns the last :class:`CoinActionResult`. The caller must skip rather
        than fail when no win occurs, because the outcome is random.
        """
        attempts = attempts or CoinSettings.GAME_WIN_ATTEMPTS
        results = []
        for _ in range(attempts):
            result = self.start_game()
            results.append(result)
            if result.status == "won" or any(
                marker in result.message.lower()
                for marker in ("you won", "you win", "congratulations")
            ):
                result.status = "won"
                result.detail["attempts"] = results
                return result
            if result.blocked:
                result.detail["attempts"] = results
                return result
        last = results[-1] if results else CoinActionResult("game_entry", False, "not_found")
        last.detail["attempts"] = results
        return last

    # --------------------------------------------------------------- profile
    def complete_profile(self, profile_data=None):
        if self.is_login_screen():
            return CoinActionResult("profile_completion", False, "login_required")
        if profile_data is None:
            raw = CoinSettings.PROFILE_DATA
            try:
                profile_data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                profile_data = {}
        if not profile_data:
            return CoinActionResult(
                "profile_completion",
                False,
                "not_found",
                "SIGNUP_PROFILE_DATA is required to complete the profile",
            )

        self.go_home()
        self._open_profile()
        edit = self._find_clickable(CoinActionLocators.EDIT_PROFILE)
        if edit is not None and "edit" in self._label(edit).lower():
            try:
                edit.click()
                time.sleep(2)
            except (StaleElementReferenceException, WebDriverException):
                pass

        filled = self._fill_profile_fields(profile_data)
        if not filled:
            return CoinActionResult(
                "profile_completion",
                False,
                "not_found",
                "Profile fields were not found",
            )
        save = self._find_clickable(CoinActionLocators.SAVE_PROFILE)
        if save is None:
            return CoinActionResult(
                "profile_completion", False, "not_found", "Profile save button was not found"
            )
        try:
            save.click()
            time.sleep(2)
        except (StaleElementReferenceException, WebDriverException) as error:
            return CoinActionResult("profile_completion", False, "error", str(error))

        status = self._wait_for_feedback()
        if status == "error":
            text = self.page_text()
            if any(marker in text for marker in ("profile updated", "saved successfully", "success")):
                status = "success"
        return CoinActionResult("profile_completion", True, status, self._feedback_message())

    def _open_profile(self):
        profile = self._find_clickable(CoinActionLocators.PROFILE_ENTRY)
        if profile is not None:
            try:
                profile.click()
                time.sleep(2)
                return True
            except (StaleElementReferenceException, WebDriverException):
                pass
        width, _ = self._screen_size()
        x, y = CoinActionLocators.HOME_MENU_TAP
        try:
            self.driver.tap([(int(x * width / 720), int(y))])
            time.sleep(2)
        except WebDriverException:
            return False
        profile = self._find_clickable(CoinActionLocators.PROFILE_ENTRY)
        if profile is not None:
            try:
                profile.click()
                time.sleep(2)
                return True
            except (StaleElementReferenceException, WebDriverException):
                pass
        return False

    def _fill_profile_fields(self, profile_data):
        filled = 0
        for label, value in profile_data.items():
            for element in self.driver.find_elements(*CoinActionLocators.FORM_INPUT):
                try:
                    hints = " ".join(
                        str(element.get_attribute(attribute) or "")
                        for attribute in ("hint", "text", "content-desc")
                    ).lower()
                except (StaleElementReferenceException, WebDriverException):
                    continue
                if label.lower() not in hints:
                    continue
                try:
                    current = (element.get_attribute("text") or "").strip()
                    if str(value) == current:
                        filled += 1
                        break
                    element.clear()
                    element.send_keys(str(value))
                    filled += 1
                    break
                except (StaleElementReferenceException, WebDriverException):
                    continue
        return filled

    # ---------------------------------------------------------------- forms
    def _fill_first_input(self, value):
        for element in self.driver.find_elements(*CoinActionLocators.FORM_INPUT):
            try:
                if not element.is_displayed():
                    continue
                element.clear()
                element.send_keys(str(value))
                return True
            except (StaleElementReferenceException, WebDriverException):
                continue
        return False

    def _submit_form(self):
        for locator in (CoinActionLocators.SUBMIT, CoinLocators.CONFIRM):
            element = self._find_clickable(locator)
            if element is not None:
                try:
                    element.click()
                    time.sleep(2)
                    return True
                except (StaleElementReferenceException, WebDriverException):
                    continue
        return False

    def _click_text(self, text):
        normalized = coin_parser.normalize_key(text)
        for element in self.driver.find_elements(
            "xpath", "//*[@clickable='true' and @content-desc!='']"
        ):
            label = coin_parser.normalize_key(self._label(element))
            if normalized and normalized in label:
                try:
                    element.click()
                    return True
                except (StaleElementReferenceException, WebDriverException):
                    continue
        return False

    # ------------------------------------------------------------- feedback
    def has_blocking_message(self):
        text = self.page_text()
        return any(
            marker in text
            for marker in (
                CoinSettings.INSUFFICIENT_MARKERS
                + CoinSettings.NOT_CHECKED_IN_MARKERS
                + CoinSettings.FEATURE_DISABLED_MARKERS
            )
        )

    def _wait_for_feedback(self, timeout=None, extra_markers=()):
        timeout = timeout or CoinSettings.FEEDBACK_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = self.classify_feedback(extra_markers=extra_markers)
            if status != "error":
                return status
            time.sleep(0.5)
        return "error"

    def _feedback_message(self):
        try:
            labels = []
            for element in self.driver.find_elements(
                "xpath", "//*[@content-desc!='' or @text!='']"
            ):
                label = self._label(element)
                if label and len(label) < 300:
                    labels.append(label)
            return "\n".join(dict.fromkeys(labels))[-1500:]
        except WebDriverException:
            return ""

    def classify_feedback(self, extra_markers=()):
        text = self.page_text()
        if any(marker in text for marker in CoinSettings.INSUFFICIENT_MARKERS):
            return "insufficient_coins"
        if any(marker in text for marker in CoinSettings.NOT_CHECKED_IN_MARKERS):
            return "not_checked_in"
        if any(marker in text for marker in CoinSettings.FEATURE_DISABLED_MARKERS):
            return "feature_unavailable"
        if any(marker in text for marker in CoinSettings.CHECKIN_PENDING_MARKERS):
            return "pending"
        if any(marker in text for marker in CoinSettings.CHECKIN_REJECTED_MARKERS):
            return "rejected"
        if extra_markers and any(marker in text for marker in extra_markers):
            if any(marker in text for marker in ("you won", "you win", "congratulations")):
                return "won"
            if any(marker in text for marker in ("you lost", "better luck")):
                return "lost"
        if any(marker in text for marker in CoinSettings.CHECKIN_SUCCESS_MARKERS):
            return "success"
        return "error"
