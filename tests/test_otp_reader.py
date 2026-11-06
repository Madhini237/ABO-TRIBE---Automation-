"""Unit tests for OTP extraction from SMS notifications (no device required)."""

from utils.otp_reader import OtpReader


def screen(*texts):
    nodes = "".join(f'<node text="{text}" />' for text in texts)
    return f"<hierarchy>{nodes}</hierarchy>"


def test_extracts_otp_from_sms_notification():
    source = screen("Your ABO Tribe OTP is 482913. Do not share it.")
    assert OtpReader.extract_otp(source) == "482913"


def test_extracts_grouped_otp():
    source = screen("Your verification code is 123 456")
    assert OtpReader.extract_otp(source) == "123456"

    source = screen("Your verification code is 12-34-56")
    assert OtpReader.extract_otp(source) == "123456"


def test_strong_otp_label_wins_over_a_promotional_number():
    source = screen(
        "Login now and win 5000 coins",
        "Your OTP is 778899",
    )
    assert OtpReader.extract_otp(source) == "778899"


def test_generic_code_word_is_not_used_on_the_app_screen():
    source = screen("Enter code for 5000 coins")

    assert OtpReader.extract_otp(source) is None
    assert OtpReader.extract_otp(source, allow_unlabelled=True) == "5000"


def test_phone_number_before_otp_is_not_used_as_otp():
    source = screen(
        "OTP sent to +91 98765 43210",
        "Your OTP is 112233",
    )
    assert OtpReader.extract_otp(source) == "112233"


def test_phone_number_alone_is_not_an_otp():
    source = screen("Your OTP was sent to 9876543210")
    assert OtpReader.extract_otp(source, allow_unlabelled=True) is None


def test_skips_previously_seen_otp():
    source = screen(
        "Your OTP is 111111",
        "Your new OTP is 222222",
    )
    assert OtpReader.extract_otp(source, exclude={"111111"}) == "222222"


def test_returns_none_when_no_otp_is_visible():
    source = screen("Enter OTP", "Resend OTP", "Continue")
    assert OtpReader.extract_otp(source) is None


def test_unlabelled_code_is_allowed_from_notifications_only():
    source = screen("482913")

    assert OtpReader.extract_otp(source, allow_unlabelled=True) == "482913"
    assert OtpReader.extract_otp(source) is None


def test_snapshot_collects_every_visible_code():
    source = screen(
        "Your OTP is 111111",
        "Your new OTP is 222222",
    )
    assert OtpReader.extract_codes(source) == ["111111", "222222"]
