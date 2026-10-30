import os
from getpass import getpass

import pytest
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait

from pages.signup_page import SignupPage

load_dotenv()


@pytest.fixture
def signup_page(driver):
    return SignupPage(driver)


def enter_manual_otp(mobile_number):
    """Read the fresh OTP without echoing it to test output."""
    otp = getpass(f"Enter the latest OTP sent to {mobile_number}: ").strip()
    assert otp, "OTP cannot be blank"
    return otp


def enter_manual_mobile_number():
    """Read the new user's phone number at test runtime."""
    mobile_number = input("Enter a new 10-digit signup mobile number: ").strip()
    SignupPage.ensure_new_mobile_number(mobile_number)
    return mobile_number


@pytest.mark.signup
@pytest.mark.negative
def test_signup_rejects_invalid_mobile_number(driver, signup_page):
    signup_page.prepare_login_screen()
    signup_page.enter_mobile_number(os.getenv("SIGNUP_INVALID_MOBILE_NUMBER", "12345"))

    if signup_page.login_button_is_enabled():
        signup_page.request_otp()

    assert signup_page.has_validation_message() or not signup_page.login_button_is_enabled(), (
        "Invalid mobile number had no validation response and Continue remained enabled"
    )
    assert not signup_page.is_otp_screen_displayed(), "OTP screen opened for an invalid mobile number"
    assert not signup_page.is_dashboard_displayed(), "Invalid mobile number unexpectedly opened the Dashboard"


@pytest.mark.signup
@pytest.mark.positive
def test_signup_new_user_and_keep_authenticated_session(driver, signup_page):
    mobile_number = enter_manual_mobile_number()
    pending_otp = signup_page.is_otp_screen_for_mobile(mobile_number)
    if not pending_otp:
        signup_page.prepare_login_screen()
        signup_page.enter_mobile_number(mobile_number)
        signup_page.request_otp()

    otp = enter_manual_otp(mobile_number)
    signup_page.enter_otp(otp)
    stage = signup_page.wait_for_registration_stage()
    if stage == "profile":
        signup_page.fill_profile_details(SignupPage.load_profile_data())
        signup_page.submit_profile_details()
    elif stage == "bonus":
        signup_page.handle_signup_bonus_dialog()

    assert signup_page.is_registration_successful(), "Signup did not complete successfully"
    assert signup_page.wait_for_dashboard(), "Dashboard was not displayed after successful signup"


@pytest.mark.signup
@pytest.mark.positive
@pytest.mark.parametrize("auth_choice", ["Login", "Sign Up"])
def test_signup_skip_profile_guest_dashboard_auth_prompt(driver, signup_page, auth_choice):
    """A new user can skip optional profile setup and choose an auth path from Coins."""
    mobile_number = enter_manual_mobile_number()
    if not signup_page.is_otp_screen_for_mobile(mobile_number):
        signup_page.prepare_login_screen()
        signup_page.enter_mobile_number(mobile_number)
        signup_page.request_otp()

    otp = enter_manual_otp(mobile_number)
    signup_page.enter_otp(otp)
    stage = signup_page.wait_for_registration_stage()
    if stage == "profile":
        signup_page.skip_profile()
    elif stage == "bonus":
        signup_page.handle_signup_bonus_dialog()
    else:
        signup_page.wait_for_dashboard()

    assert signup_page.is_dashboard_displayed(), "Dashboard did not open after skipping profile setup"
    signup_page.open_coins_as_guest()
    WebDriverWait(driver, 10).until(lambda _: signup_page.guest_auth_choice_is_displayed())
    signup_page.choose_guest_auth(auth_choice)
    assert signup_page.auth_phone_entry_is_displayed(), (
        f"Selecting {auth_choice} from the guest prompt did not open phone authentication"
    )
