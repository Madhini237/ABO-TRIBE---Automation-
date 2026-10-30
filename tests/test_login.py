import os

import pytest
from dotenv import load_dotenv

from pages.login_page import LoginPage

load_dotenv()


@pytest.fixture
def login_page(driver):
    return LoginPage(driver)


def required_env(name):
    value = os.getenv(name)
    assert value, f"{name} must be configured in .env"
    return value


def enter_manual_mobile_number():
    mobile_number = input("Enter a 10-digit mobile number for the resend OTP test: ").strip()
    digits = "".join(character for character in mobile_number if character.isdigit())
    assert len(digits) == 10, "Enter a valid 10-digit mobile number"
    return digits


def negative_test_mobile_number():
    configured = os.getenv("NEGATIVE_TEST_MOBILE_NUMBER")
    valid_number = required_env("TEST_MOBILE_NUMBER")
    if configured:
        assert configured != valid_number, "Negative test number must differ from TEST_MOBILE_NUMBER"
        return configured

    # Use a separate 10-digit India mobile-format number when no test number
    # is configured. Keep it distinct from the configured and sample numbers.
    fixed_numbers = {valid_number, "9999999999"}
    candidate = 6_000_000_001
    while candidate < 10_000_000_000:
        number = str(candidate)
        if number not in fixed_numbers:
            return number
        candidate += 1
    raise AssertionError("Could not derive a distinct negative test number")


@pytest.mark.login
@pytest.mark.positive
def test_successful_login_and_logout(driver, login_page):
    mobile_number = required_env("TEST_MOBILE_NUMBER")
    otp = required_env("TEST_OTP")

    login_page.prepare_login_screen()
    login_page.enter_mobile_number(mobile_number)
    login_page.request_otp()
    login_page.enter_otp(otp)
    login_page.verify_otp()

    assert login_page.is_dashboard_displayed(), "Dashboard was not displayed after OTP verification"
    login_page.logout()


@pytest.mark.login
@pytest.mark.negative
def test_invalid_otp_for_different_mobile_number(driver, login_page):
    mobile_number = negative_test_mobile_number()
    invalid_otp = required_env("INVALID_TEST_OTP")

    login_page.prepare_login_screen()
    login_page.enter_mobile_number(mobile_number)
    login_page.request_otp()
    login_page.enter_otp(invalid_otp)
    login_page.verify_otp()

    assert login_page.has_invalid_otp_feedback(), "Invalid OTP validation response was not displayed"
    login_page.dismiss_otp_feedback()
    assert login_page.is_otp_screen_displayed(), "Invalid OTP unexpectedly left the OTP verification screen"
    assert not login_page.is_dashboard_displayed(), "Invalid OTP unexpectedly opened the Dashboard"


@pytest.mark.login
def test_resend_otp(driver, login_page):
    mobile_number = enter_manual_mobile_number()

    login_page.prepare_login_screen()
    login_page.enter_mobile_number(mobile_number)
    login_page.request_otp()
    login_page.resend_otp()

    assert login_page.is_otp_screen_displayed(), "OTP verification screen disappeared after resend"
