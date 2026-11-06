"""Unit tests for the shared manual-phone + captured-OTP flow."""

import pytest

from utils import auth_flow


class FakePage:
    def __init__(self):
        self.calls = []

    def enter_mobile_number(self, mobile_number):
        self.calls.append(("enter", mobile_number))

    def request_otp(self):
        self.calls.append(("request",))


class FakeReader:
    def __init__(self, code="123456", existing=None):
        self.code = code
        self.existing = existing or {"111111"}
        self.snapshot_numbers = []
        self.read_kwargs = None

    def snapshot_codes(self, mobile_number):
        self.snapshot_numbers.append(mobile_number)
        return set(self.existing)

    def read_otp(self, **kwargs):
        self.read_kwargs = kwargs
        return self.code


def test_prompt_mobile_number_validates_and_normalizes(monkeypatch):
    validated = []
    monkeypatch.setattr("builtins.input", lambda _: "98765-43210")

    digits = auth_flow.prompt_mobile_number("Phone: ", validator=validated.append)

    assert digits == "9876543210"
    assert validated == ["9876543210"]


def test_prompt_mobile_number_rejects_wrong_length(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "12345")

    with pytest.raises(AssertionError):
        auth_flow.prompt_mobile_number()


def test_request_otp_and_capture_excludes_codes_seen_before_request():
    page = FakePage()
    reader = FakeReader()

    otp = auth_flow.request_otp_and_capture(
        None,
        page,
        "9876543210",
        otp_reader=reader,
    )

    assert otp == "123456"
    assert page.calls == [("enter", "9876543210"), ("request",)]
    assert reader.snapshot_numbers == ["9876543210"]
    assert reader.read_kwargs == {
        "mobile_number": "9876543210",
        "exclude": {"111111"},
        "timeout": None,
    }


def test_request_otp_and_capture_runs_before_request_callback():
    page = FakePage()
    reader = FakeReader()

    def apply_referral():
        page.calls.append(("referral",))

    auth_flow.request_otp_and_capture(
        None,
        page,
        "9876543210",
        otp_reader=reader,
        before_request=apply_referral,
    )

    assert page.calls == [
        ("enter", "9876543210"),
        ("referral",),
        ("request",),
    ]


class FakeLogin:
    def __init__(self):
        self.prepared = 0
        self.entered_otp = None
        self.verified = 0

    def prepare_login_screen(self):
        self.prepared += 1

    def enter_otp(self, otp):
        self.entered_otp = otp

    def verify_otp(self):
        self.verified += 1


def test_login_with_captured_otp_runs_the_shared_flow(monkeypatch):
    login = FakeLogin()
    captured = {}

    monkeypatch.setattr(auth_flow, "LoginPage", lambda driver: login)

    def fake_capture(driver, page, mobile_number):
        captured["page"] = page
        captured["mobile"] = mobile_number
        return "654321"

    monkeypatch.setattr(auth_flow, "request_otp_and_capture", fake_capture)

    result = auth_flow.login_with_captured_otp(object(), "9876543210")

    assert result is login
    assert login.prepared == 1
    assert login.entered_otp == "654321"
    assert login.verified == 1
    assert captured == {"page": login, "mobile": "9876543210"}
