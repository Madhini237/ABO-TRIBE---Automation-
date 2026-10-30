import json
import os
import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.config import Config
from pages.login_page import LoginPage


class SignupPage:
    """Actions for ABO Tribe's new-user OTP signup flow."""

    PHONE_FIELD = LoginPage.MOBILE_NUMBER
    CONTINUE_BUTTON = LoginPage.LOGIN_BUTTON
    OTP_FIELD = LoginPage.OTP_FIELD
    OTP_SCREEN = (
        AppiumBy.XPATH,
        "//*[contains(@content-desc,'Verify') or contains(@text,'Verify') or contains(@content-desc,'Resend OTP') or contains(@text,'Resend OTP')]",
    )
    PROFILE_SUBMIT_BUTTON = (
        AppiumBy.XPATH,
        "//*[contains(translate(@content-desc,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'continue') or contains(translate(@content-desc,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'submit') or contains(translate(@content-desc,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'register') or contains(translate(@content-desc,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'finish') or contains(translate(@content-desc,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'save') or contains(translate(@text,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'continue') or contains(translate(@text,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'submit') or contains(translate(@text,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'register') or contains(translate(@text,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'finish') or contains(translate(@text,'CONTINUESUBMITREGISTERFINISHSAVE','continuesubmitregisterfinishsave'),'save')]",
    )
    VALIDATION_MESSAGE = (
        AppiumBy.XPATH,
        "//*[contains(translate(@text,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'invalid') or contains(translate(@content-desc,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'invalid') or contains(translate(@text,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'error') or contains(translate(@content-desc,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'error') or contains(translate(@text,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'valid mobile') or contains(translate(@content-desc,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'valid mobile') or contains(translate(@text,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'phone number') or contains(translate(@content-desc,'INVALIDERRORVALIDMOBILEPHONE','invaliderrorvalidmobilephone'),'phone number')]",
    )
    SKIP_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Skip")
    COINS_ENTRY = (
        AppiumBy.XPATH,
        "//*[contains(translate(@content-desc,'COINS','coins'),'coins') or contains(translate(@text,'COINS','coins'),'coins')]",
    )

    PROFILE_MARKERS = (
        "complete your profile",
        "profile details",
        "tell us about",
        "full name",
        "first name",
        "last name",
        "email address",
        "date of birth",
    )
    BONUS_DIALOG_MARKERS = (
        "signup bonus",
        "sign up bonus",
        "welcome bonus",
        "bonus coins",
        "coins added",
        "earned coins",
    )
    BONUS_DIALOG_ACTIONS = (
        AppiumBy.XPATH,
        "//*[contains(translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue') or contains(translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue') or contains(translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'claim') or contains(translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'claim') or contains(translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'got it') or contains(translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'got it') or translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='ok' or translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='ok' or contains(translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'close') or contains(translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'close')]",
    )

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)
        self.login_page = LoginPage(driver)

    @staticmethod
    def _digits(value):
        return "".join(character for character in str(value) if character.isdigit())

    def prepare_login_screen(self):
        self.login_page.prepare_login_screen()

    def enter_mobile_number(self, mobile_number):
        self.login_page.enter_mobile_number(mobile_number)

    def request_otp(self):
        self.login_page.request_otp()

    def enter_otp(self, otp):
        self.login_page.enter_otp(otp)
        self.login_page.verify_otp()

    def is_otp_screen_displayed(self):
        return bool(self.driver.find_elements(*self.OTP_SCREEN))

    def is_dashboard_displayed(self):
        return bool(self.driver.find_elements(*LoginPage.DASHBOARD))

    def has_validation_message(self):
        return bool(self.driver.find_elements(*self.VALIDATION_MESSAGE))

    def login_button_is_enabled(self):
        try:
            return self.driver.find_element(*self.CONTINUE_BUTTON).is_enabled()
        except Exception:
            return False

    def is_profile_form_displayed(self):
        source = self.driver.page_source.lower()
        if any(marker in source for marker in self.PROFILE_MARKERS):
            return True

        for field in self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText"):
            labels = " ".join(
                field.get_attribute(attribute) or ""
                for attribute in ("hint", "text", "contentDescription")
            ).lower()
            if any(marker in labels for marker in self.PROFILE_MARKERS) or any(term in labels for term in ("name", "email", "gender", "birth", "dob")):
                return True
        return False

    def wait_for_registration_stage(self, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.driver.find_elements(*LoginPage.INVALID_OTP_MESSAGE):
                raise AssertionError("OTP verification was rejected during signup")
            if self.is_profile_form_displayed():
                return "profile"
            if self.is_signup_bonus_dialog_displayed():
                return "bonus"
            if self.is_dashboard_displayed():
                return "dashboard"
            time.sleep(0.25)
        raise TimeoutException("Neither the profile form nor Dashboard appeared after OTP verification")

    def is_signup_bonus_dialog_displayed(self):
        source = self.driver.page_source.lower()
        return any(marker in source for marker in self.BONUS_DIALOG_MARKERS)

    def handle_signup_bonus_dialog(self, timeout=45):
        """Dismiss the signup bonus prompt when it has an action, then await Dashboard."""
        if self.is_signup_bonus_dialog_displayed():
            actions = self.driver.find_elements(*self.BONUS_DIALOG_ACTIONS)
            for action in actions:
                try:
                    if action.is_displayed() and action.is_enabled():
                        action.click()
                        break
                except Exception:
                    continue
        return self.wait_for_dashboard(timeout=timeout)

    @staticmethod
    def load_profile_data():
        raw_data = os.getenv("SIGNUP_PROFILE_DATA", "{}").strip()
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as error:
            raise AssertionError("SIGNUP_PROFILE_DATA must be a JSON object keyed by visible profile field labels") from error
        if not isinstance(data, dict):
            raise AssertionError("SIGNUP_PROFILE_DATA must be a JSON object")
        if not data:
            raise AssertionError(
                "The app prompted for profile details; configure SIGNUP_PROFILE_DATA with the visible field labels and test values"
            )
        return data

    @staticmethod
    def _xpath_literal(value):
        value = str(value)
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"

    def fill_profile_details(self, profile_data):
        for label, value in profile_data.items():
            literal = self._xpath_literal(label)
            locator = (
                AppiumBy.XPATH,
                f"//android.widget.EditText[@hint={literal} or @text={literal} or @content-desc={literal}]",
            )
            field = self.wait.until(EC.visibility_of_element_located(locator))
            field.clear()
            field.send_keys(str(value))

    def submit_profile_details(self):
        self.wait.until(EC.element_to_be_clickable(self.PROFILE_SUBMIT_BUTTON)).click()

    def skip_profile(self):
        """Skip optional profile completion and verify the guest dashboard opens."""
        skip = self.wait.until(EC.element_to_be_clickable(self.SKIP_BUTTON))
        skip.click()
        self.wait_for_dashboard()

    def open_coins_as_guest(self):
        self.wait.until(EC.element_to_be_clickable(self.COINS_ENTRY)).click()

    def guest_auth_choice_is_displayed(self):
        source = self.driver.page_source.lower()
        has_login = "login" in source or "log in" in source
        has_signup = "sign up" in source or "signup" in source
        return has_login and has_signup

    def choose_guest_auth(self, choice):
        normalized = choice.strip().lower()
        if normalized == "login":
            labels = ("Login", "Log In")
        elif normalized in ("sign up", "signup"):
            labels = ("Sign Up", "Signup")
        else:
            raise ValueError("choice must be 'Login' or 'Sign Up'")
        for label in labels:
            matches = self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, label)
            if not matches:
                matches = self.driver.find_elements(
                    AppiumBy.XPATH,
                    f"//*[translate(@text,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='{label.lower()}' or translate(@content-desc,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='{label.lower()}']",
                )
            if matches:
                matches[0].click()
                return
        raise AssertionError(f"Guest authentication dialog did not expose a {choice} action")

    def auth_phone_entry_is_displayed(self):
        return bool(self.driver.find_elements(*self.PHONE_FIELD))

    def is_registration_successful(self):
        if self.is_dashboard_displayed():
            return True
        source = self.driver.page_source.lower()
        return any(
            phrase in source
            for phrase in ("registration successful", "signup successful", "sign up successful", "welcome")
        )

    @staticmethod
    def ensure_new_mobile_number(mobile_number):
        phone = SignupPage._digits(mobile_number)[-10:]
        fixed_phone = SignupPage._digits(Config.VALID_PHONE)[-10:]
        saved_phone = SignupPage._digits(os.getenv("TEST_MOBILE_NUMBER", ""))[-10:]
        assert len(phone) == 10, "SIGNUP_MOBILE_NUMBER must contain a 10-digit mobile number"
        assert phone != fixed_phone and phone != saved_phone, (
            "SIGNUP_MOBILE_NUMBER must differ from the saved and fixed test numbers"
        )






    def wait_for_dashboard(self, timeout=30):
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(LoginPage.DASHBOARD)
        )
        return True

    def is_otp_screen_for_mobile(self, mobile_number):
        if not self.is_otp_screen_displayed():
            return False
        expected = self._digits(mobile_number)[-10:]
        return bool(expected) and expected in self._digits(self.driver.page_source)
