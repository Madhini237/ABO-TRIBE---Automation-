"""Capture login/signup OTPs from the device UI instead of a fixed value.

The OTP is delivered as an SMS notification. ``OtpReader`` polls the current
app screen first (a heads-up notification is sometimes part of the visible
hierarchy) and then the Android notification shade. Nothing is entered until a
real code is found, so the tests exercise the same flow a user follows.
"""

import html
import os
import re
import time

DEFAULT_OTP_TIMEOUT = 120


class OtpReader:
    """Read the latest OTP from the app screen or the notification shade."""

    # 4-8 digits, optionally grouped like "123 456" or "123-456".
    # A newline is a node boundary, so it is never used as a group separator.
    _CODE_RE = re.compile(r"(?<!\d)(?:\d[ \t-]?){4,8}(?!\d)")
    _STRONG_CONTEXT_RE = re.compile(
        r"(?i)\b(?:otp|one[\s-]?time(?:\s+(?:password|code))?|"
        r"verification\s+code|security\s+code|passcode)\b"
    )
    _WEAK_CONTEXT_RE = re.compile(
        r"(?i)\b(?:verification|security|login|code)\b"
    )
    _ATTR_RE = re.compile(r'(?:text|content-desc)="([^"]*)"')

    def __init__(self, driver, timeout=None, poll_interval=None):
        self.driver = driver
        self.timeout = timeout or int(
            os.getenv("OTP_WAIT_TIMEOUT", str(DEFAULT_OTP_TIMEOUT))
        )
        self.poll_interval = poll_interval or float(
            os.getenv("OTP_POLL_INTERVAL", "2")
        )

    # --------------------------------------------------------------- parsing
    @staticmethod
    def _digits(value):
        return "".join(character for character in str(value or "") if character.isdigit())

    @classmethod
    def _screen_text(cls, page_source):
        """Return the readable text of a UiAutomator page-source dump."""
        source = page_source or ""
        attributes = cls._ATTR_RE.findall(source)
        if attributes:
            return "\n".join(html.unescape(value) for value in attributes)
        return html.unescape(source)

    @staticmethod
    def _is_standalone(text, match):
        """Reject a fragment of a longer, space-separated number.

        A phone number such as ``98765 43210`` would otherwise expose partial
        matches like ``98765``. Newlines are treated as boundaries so values
        from different UI nodes cannot interfere with each other.
        """
        before = text[: match.start()]
        after = text[match.end() :]
        if re.search(r"\d[ \t-]*$", before):
            return False
        if re.match(r"[ \t-]*\d", after):
            return False
        return True

    @classmethod
    def extract_codes(cls, page_source, mobile_number=None):
        """Return every OTP-shaped code found on the screen, newest first."""
        text = cls._screen_text(page_source)
        recipient = cls._digits(mobile_number)[-10:]
        codes = []
        for match in cls._CODE_RE.finditer(text):
            if not cls._is_standalone(text, match):
                continue
            code = cls._digits(match.group(0))
            if not 4 <= len(code) <= 8:
                continue
            if recipient and code == recipient:
                continue
            if code not in codes:
                codes.append(code)
        return codes

    @classmethod
    def extract_otp(
        cls,
        page_source,
        mobile_number=None,
        exclude=(),
        allow_unlabelled=False,
    ):
        """Return the first plausible OTP, or ``None`` when none is visible.

        A code next to a word such as "OTP", "verification code" or "passcode"
        always wins. Notifications commonly show the code without that label,
        so ``allow_unlabelled`` enables a 6-digit fallback for the shade while
        keeping the app screen strict.
        """
        text = cls._screen_text(page_source)
        recipient = cls._digits(mobile_number)[-10:]
        excluded = {cls._digits(value) for value in exclude if cls._digits(value)}
        weak_fallback = None
        unlabelled_fallback = None

        for match in cls._CODE_RE.finditer(text):
            if not cls._is_standalone(text, match):
                continue
            code = cls._digits(match.group(0))
            if not 4 <= len(code) <= 8:
                continue
            if recipient and code == recipient:
                continue
            if code in excluded:
                continue

            # Context is matched within the same UI node (line); otherwise a
            # button label from the next node could make a random number
            # look like an OTP.
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            window = text[max(line_start, match.start() - 60) : min(line_end, match.end() + 20)]
            if cls._STRONG_CONTEXT_RE.search(window):
                return code
            if weak_fallback is None and cls._WEAK_CONTEXT_RE.search(window):
                weak_fallback = code
            if unlabelled_fallback is None and len(code) == 6:
                unlabelled_fallback = code

        if allow_unlabelled:
            return weak_fallback or unlabelled_fallback
        return None

    # -------------------------------------------------------------- reading
    def _page_source(self):
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def _open_notifications(self):
        open_notifications = getattr(self.driver, "open_notifications", None)
        if callable(open_notifications):
            try:
                open_notifications()
                time.sleep(1)
                return True
            except Exception:
                pass

        try:
            self.driver.execute_script(
                "mobile: shell",
                {
                    "command": "cmd",
                    "args": ["statusbar", "expand-notifications"],
                },
            )
            time.sleep(1)
            return True
        except Exception:
            return False

    def _notification_shade_visible(self):
        # Only the system UI package proves that the shade is still open.
        return "com.android.systemui" in self._page_source()

    def _close_notifications(self):
        try:
            self.driver.execute_script(
                "mobile: shell",
                {"command": "cmd", "args": ["statusbar", "collapse"]},
            )
            time.sleep(0.5)
        except Exception:
            pass

        if self._notification_shade_visible():
            try:
                self.driver.back()
            except Exception:
                pass

    def snapshot_codes(self, mobile_number=None):
        """Return codes already visible before a new OTP is requested.

        Passing this set as ``exclude`` to :meth:`read_otp` prevents an old SMS
        notification from being mistaken for the freshly generated OTP.
        """
        codes = set(self.extract_codes(self._page_source(), mobile_number))
        if self._open_notifications():
            try:
                codes.update(
                    self.extract_codes(self._page_source(), mobile_number)
                )
            finally:
                self._close_notifications()
        return codes

    def read_otp(self, mobile_number=None, exclude=(), timeout=None):
        """Poll the screen and notification shade until an OTP arrives."""
        wait_seconds = timeout or self.timeout
        deadline = time.monotonic() + wait_seconds
        excluded = set(exclude or ())

        while True:
            # A heads-up notification may already be part of the app hierarchy.
            code = self.extract_otp(
                self._page_source(),
                mobile_number=mobile_number,
                exclude=excluded,
                allow_unlabelled=False,
            )
            if code:
                return code

            if self._open_notifications():
                try:
                    code = self.extract_otp(
                        self._page_source(),
                        mobile_number=mobile_number,
                        exclude=excluded,
                        allow_unlabelled=True,
                    )
                finally:
                    self._close_notifications()
                if code:
                    return code

            if time.monotonic() >= deadline:
                break
            time.sleep(self.poll_interval)

        raise AssertionError(
            "No OTP SMS notification was found within "
            f"{wait_seconds}s for {mobile_number or 'the entered mobile number'}. "
            "Make sure the test device can receive the SMS and notifications are enabled."
        )
