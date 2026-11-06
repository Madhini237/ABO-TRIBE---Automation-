"""Shared interactive phone-authentication helpers.

Login and signup tests ask for the mobile number at runtime and capture the
OTP from the SMS notification on the device. Keeping the flow here lets the
login, signup and coin suites reuse exactly the same behaviour.
"""

from pages.login_page import LoginPage
from utils.otp_reader import OtpReader


def prompt_mobile_number(
    prompt="Enter your 10-digit mobile number: ",
    validator=None,
):
    """Ask the tester for a mobile number and return its 10 digits."""
    mobile_number = input(prompt).strip()
    digits = "".join(character for character in mobile_number if character.isdigit())
    assert len(digits) == 10, "Enter a valid 10-digit mobile number"
    if validator is not None:
        validator(digits)
    return digits


def request_otp_and_capture(
    driver,
    auth_page,
    mobile_number,
    otp_reader=None,
    timeout=None,
    before_request=None,
):
    """Enter the mobile number, request an OTP and read the new SMS code.

    ``auth_page`` is any page exposing ``enter_mobile_number`` and
    ``request_otp`` (``LoginPage`` or ``SignupPage``). Codes already visible
    before the request are excluded so an old SMS is never reused.
    ``before_request`` runs after the number is entered and before the OTP is
    requested, which lets signup flows apply a referral code.
    """
    reader = otp_reader or OtpReader(driver)
    existing_codes = reader.snapshot_codes(mobile_number)
    auth_page.enter_mobile_number(mobile_number)
    if before_request is not None:
        before_request()
    auth_page.request_otp()
    return reader.read_otp(
        mobile_number=mobile_number,
        exclude=existing_codes,
        timeout=timeout,
    )


def login_with_captured_otp(driver, mobile_number, prepare=True):
    """Sign in with a manually supplied number and the received SMS OTP."""
    login = LoginPage(driver)
    if prepare:
        login.prepare_login_screen()
    otp = request_otp_and_capture(driver, login, mobile_number)
    login.enter_otp(otp)
    login.verify_otp()
    return login
