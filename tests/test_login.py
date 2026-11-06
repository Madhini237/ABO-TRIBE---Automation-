import os

import pytest
from dotenv import load_dotenv

from pages.login_page import LoginPage
from utils.auth_flow import prompt_mobile_number, request_otp_and_capture

load_dotenv()


@pytest.fixture
def login_page(driver):
    return LoginPage(driver)


def required_env(name):
    value = os.getenv(name)
    assert value, f"{name} must be configured in .env"
    return value


def negative_test_mobile_number():
    configured = os.getenv("NEGATIVE_TEST_MOBILE_NUMBER")
    saved_number = "".join(
        character
        for character in os.getenv("TEST_MOBILE_NUMBER", "")
        if character.isdigit()
    )
    if configured:
        assert configured != saved_number, "Negative test number must differ from TEST_MOBILE_NUMBER"
        return configured

    # Use a separate 10-digit India mobile-format number when no test number
    # is configured. Keep it distinct from any saved and sample numbers.
    fixed_numbers = {"9999999999"}
    if saved_number:
        fixed_numbers.add(saved_number)
    candidate = 6_000_000_001
    while candidate < 10_000_000_000:
        number = str(candidate)
        if number not in fixed_numbers:
            return number
        candidate += 1
    raise AssertionError("Could not derive a distinct negative test number")


@pytest.mark.login
@pytest.mark.positive
def test_successful_login_with_manual_mobile_and_screen_otp(driver, login_page):
    mobile_number = prompt_mobile_number(
        "Enter your 10-digit mobile number to receive a live OTP: "
    )

    login_page.prepare_login_screen()
    otp = request_otp_and_capture(driver, login_page, mobile_number)
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
    mobile_number = prompt_mobile_number()

    login_page.prepare_login_screen()
    login_page.enter_mobile_number(mobile_number)
    login_page.request_otp()
    login_page.resend_otp()

    assert login_page.is_otp_screen_displayed(), "OTP verification screen disappeared after resend"
