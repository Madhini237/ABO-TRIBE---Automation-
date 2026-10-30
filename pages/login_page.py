from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class LoginPage:
    """Page actions for the ABO Tribe Android login and logout flows."""

    APP_PACKAGE = "com.coredot.abo.abo_bar"
    APP_COMPONENT = "com.coredot.abo.abo_bar/com.coredot.abo.abo_bar.MainActivity"
    MOBILE_NUMBER = (AppiumBy.XPATH, "//android.widget.EditText[@hint='10-digit mobile number']")
    LOGIN_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Login")
    OTP_FIELD = (AppiumBy.XPATH, "//android.widget.EditText")
    VERIFY_BUTTON = (
        AppiumBy.XPATH,
        "//android.widget.Button[contains(@content-desc,'Verify') or contains(@text,'Verify') or contains(@content-desc,'Submit') or contains(@text,'Submit')]",
    )
    RESEND_OTP_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Resend OTP")
    DASHBOARD = (
        AppiumBy.XPATH,
        "//*[contains(@content-desc,'Home') or contains(@content-desc,'Dashboard') or contains(@text,'Dashboard')]",
    )
    PROFILE_HEADER = (AppiumBy.ACCESSIBILITY_ID, "Profile")
    LOGOUT_ACTION = (AppiumBy.ACCESSIBILITY_ID, "Log out")
    INVALID_OTP_MESSAGE = (
        AppiumBy.XPATH,
        "//*[contains(translate(@text,'INVALIDWRONGINCORRECT','invalidwrongincorrect'),'invalid') or contains(translate(@content-desc,'INVALIDWRONGINCORRECT','invalidwrongincorrect'),'invalid') or contains(translate(@text,'INVALIDWRONGINCORRECT','invalidwrongincorrect'),'wrong') or contains(translate(@content-desc,'INVALIDWRONGINCORRECT','invalidwrongincorrect'),'wrong') or contains(translate(@text,'INVALIDWRONGINCORRECT','invalidwrongincorrect'),'incorrect') or contains(translate(@content-desc,'INVALIDWRONGINCORRECT','invalidwrongincorrect'),'incorrect')]",
    )
    ALERT_OK = (AppiumBy.ACCESSIBILITY_ID, "OK")

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def _launch_login_activity(self):
        # Discard a stale OTP view without clearing app data or its signed-in state.
        self.driver.terminate_app(self.APP_PACKAGE)
        self.driver.execute_script("mobile: startActivity", {"component": self.APP_COMPONENT})
        self.wait.until(EC.visibility_of_element_located(self.MOBILE_NUMBER))

    def prepare_login_screen(self):
        """Return to phone entry from onboarding, profile, OTP, or dashboard."""
        if self._is_present(self.ALERT_OK):
            self.driver.find_element(*self.ALERT_OK).click()
        if self._is_present(self.MOBILE_NUMBER):
            return
        if self._is_present(self.PROFILE_HEADER) or self.is_dashboard_displayed():
            self.logout()
            return
        if self._is_present(self.OTP_FIELD) or self.driver.current_package != self.APP_PACKAGE:
            self._launch_login_activity()
            return
        skip = self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, "Skip")
        if skip:
            skip[0].click()
        self.wait.until(EC.visibility_of_element_located(self.MOBILE_NUMBER))

    def _is_present(self, locator):
        try:
            return self.driver.find_element(*locator).is_displayed()
        except Exception:
            return False

    def enter_mobile_number(self, mobile_number):
        field = self.wait.until(EC.visibility_of_element_located(self.MOBILE_NUMBER))
        field.clear()
        field.send_keys(mobile_number)

    def request_otp(self):
        self.wait.until(EC.element_to_be_clickable(self.LOGIN_BUTTON)).click()
        self.wait.until(EC.visibility_of_element_located(self.OTP_FIELD))

    def enter_otp(self, otp):
        field = self.wait.until(EC.visibility_of_element_located(self.OTP_FIELD))
        field.clear()
        field.send_keys(otp)

    def verify_otp(self):
        # ABO Tribe may auto-verify on the last digit or enable its Verify button.
        try:
            buttons = self.driver.find_elements(*self.VERIFY_BUTTON)
            if buttons:
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(self.VERIFY_BUTTON)
                ).click()
        except (StaleElementReferenceException, TimeoutException):
            # The OTP view may be replaced during auto-verification.
            pass

    def resend_otp(self, timeout=120):
        """Wait for the resend countdown to enable the control, then tap it."""
        resend_button = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(self.RESEND_OTP_BUTTON)
        )
        resend_button.click()

    def is_dashboard_displayed(self):
        try:
            self.wait.until(EC.visibility_of_element_located(self.DASHBOARD))
            return True
        except TimeoutException:
            return False

    def is_otp_screen_displayed(self):
        try:
            self.wait.until(EC.visibility_of_element_located(self.OTP_FIELD))
            return True
        except TimeoutException:
            return False

    def has_invalid_otp_feedback(self):
        try:
            self.wait.until(EC.visibility_of_element_located(self.INVALID_OTP_MESSAGE))
            return True
        except TimeoutException:
            return False

    def dismiss_otp_feedback(self):
        self.wait.until(EC.element_to_be_clickable(self.ALERT_OK)).click()

    def logout(self):
        # The menu icon beside the coins balance has no accessibility label.
        if not self._is_present(self.PROFILE_HEADER):
            self.driver.tap([(660, 107)])
            self.wait.until(EC.visibility_of_element_located(self.PROFILE_HEADER))

        self.driver.execute_script(
            "mobile: scrollGesture",
            {"left": 24, "top": 176, "width": 672, "height": 1300,
             "direction": "down", "percent": 0.9},
        )
        self.driver.find_element(*self.LOGOUT_ACTION).click()
        self.wait.until(lambda d: len(d.find_elements(*self.LOGOUT_ACTION)) >= 1)
        self.driver.find_elements(*self.LOGOUT_ACTION)[-1].click()
        self.wait.until(EC.visibility_of_element_located(self.MOBILE_NUMBER))

