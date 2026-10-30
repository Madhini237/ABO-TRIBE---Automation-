import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import LocationSettings
from utils.ui_locators import AndroidSettingsLocators


@dataclass
class DeviceSnapshot:
    fine_location: bool
    coarse_location: bool
    location_mode: int
    airplane_mode: int
    wifi_on: int
    mobile_data: int


class Adb:
    """Thin, test-friendly wrapper around the adb CLI."""

    def __init__(self, serial: Optional[str] = None):
        self.serial = serial or os.getenv("ANDROID_UDID") or os.getenv("DEVICE_UDID")

    def command(self, *args, timeout=60):
        command = ["adb"]
        if self.serial:
            command.extend(["-s", self.serial])
        command.extend(str(arg) for arg in args)
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)

    def shell(self, *args, timeout=60):
        return self.command("shell", *args, timeout=timeout)

    def output(self, *args, timeout=60):
        result = self.shell(*args, timeout=timeout)
        return (result.stdout or "") + (result.stderr or "")


class DeviceController:
    """Controls the Android state required by the location flows.

    Appium/adb on this physical device cannot grant runtime permissions or write
    secure settings directly, so permission and location-service changes are
    performed through the real Settings UI. Network state is controlled with
    adb, which does work on the test device.
    """

    def __init__(self, driver, adb: Optional[Adb] = None):
        self.driver = driver
        self.adb = adb or Adb()
        self.wait = WebDriverWait(driver, LocationSettings.SETTINGS_TIMEOUT)

    # ------------------------------------------------------------------ app
    def start_app(self, wait_seconds=5):
        self.driver.terminate_app(LocationSettings.APP_PACKAGE)
        self.driver.execute_script(
            "mobile: startActivity",
            {"component": LocationSettings.APP_COMPONENT},
        )
        time.sleep(wait_seconds)

    def stop_app(self):
        self.driver.terminate_app(LocationSettings.APP_PACKAGE)

    def app_is_foreground(self):
        return self.driver.current_package == LocationSettings.APP_PACKAGE

    def ensure_app_foreground(self):
        if not self.app_is_foreground():
            self.start_app()

    # ------------------------------------------------------------- snapshots
    def snapshot(self):
        package_dump = self.adb.output("dumpsys", "package", LocationSettings.APP_PACKAGE)
        fine = self._granted(package_dump, "ACCESS_FINE_LOCATION")
        coarse = self._granted(package_dump, "ACCESS_COARSE_LOCATION")
        return DeviceSnapshot(
            fine_location=fine,
            coarse_location=coarse,
            location_mode=self._int_setting("secure", "location_mode", 0),
            airplane_mode=self._int_setting("global", "airplane_mode_on", 0),
            wifi_on=self._int_setting("global", "wifi_on", 1),
            mobile_data=self._int_setting("global", "mobile_data", 1),
        )

    def restore(self, snapshot: DeviceSnapshot):
        """Best-effort restoration of the device state captured by snapshot()."""
        if not LocationSettings.RESTORE_DEVICE_STATE:
            return

        self.set_network(snapshot.airplane_mode == 0)
        if snapshot.airplane_mode:
            self.set_airplane_mode(True)
        if snapshot.location_mode in (0, 1):
            self.set_location_services(False)
        else:
            self.set_location_services(True)
        self.set_location_permission(
            allow=snapshot.fine_location or snapshot.coarse_location,
            restart_app=False,
        )
        self.start_app()

    @staticmethod
    def _granted(package_dump, permission):
        match = re.search(rf"{permission}: granted=(true|false)", package_dump)
        return bool(match and match.group(1) == "true")

    def _int_setting(self, namespace, key, default=0):
        try:
            raw = self.adb.shell("settings", "get", namespace, key).stdout.strip()
            return int(raw)
        except (ValueError, subprocess.SubprocessError):
            return default

    # --------------------------------------------------------- location perm
    def location_permission_granted(self):
        package_dump = self.adb.output("dumpsys", "package", LocationSettings.APP_PACKAGE)
        return self._granted(package_dump, "ACCESS_FINE_LOCATION") or self._granted(
            package_dump, "ACCESS_COARSE_LOCATION"
        )

    def set_location_permission(self, allow: bool, restart_app=True):
        """Set the app's location permission through the Settings UI."""
        self._ensure_location_permission_page()

        radio = (
            AndroidSettingsLocators.LOCATION_ALLOW_FOREGROUND
            if allow
            else AndroidSettingsLocators.LOCATION_DENY
        )
        element = self._wait_any(radio)
        if element is None:
            raise AssertionError(f"Could not find the location permission option: {radio}")
        element.click()
        time.sleep(2)

        granted = self.location_permission_granted()
        if granted != allow:
            raise AssertionError(
                f"Location permission did not change to allow={allow} (current={granted})"
            )

        if restart_app:
            self.start_app()

    # ------------------------------------------------------ location services
    def location_services_enabled(self):
        return self._int_setting("secure", "location_mode", 0) in (1, 2, 3)

    def set_location_services(self, enabled: bool, restart_app=True):
        self.adb.shell(
            "am", "start", "-a", "android.settings.LOCATION_SOURCE_SETTINGS"
        )
        switch = self._wait_any(AndroidSettingsLocators.LOCATION_SWITCH)
        if switch is None:
            raise AssertionError("Could not find the system location services switch")

        is_on = (switch.get_attribute("text") or "").strip().lower() == "on"
        if is_on != enabled:
            bounds = switch.get_attribute("bounds") or ""
            match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
            if not match:
                switch.click()
            else:
                self.driver.tap(
                    [(
                        (int(match.group(1)) + int(match.group(3))) // 2,
                        (int(match.group(2)) + int(match.group(4))) // 2,
                    )]
                )
            time.sleep(3)

        switch = self._wait_any(AndroidSettingsLocators.LOCATION_SWITCH)
        final_state = (switch.get_attribute("text") or "").strip().lower() == "on" if switch else None
        if final_state is not None and final_state != enabled:
            raise AssertionError(
                f"Location services did not change to enabled={enabled} (current={final_state})"
            )

        if restart_app:
            self.start_app()

    def open_location_permission_settings(self):
        """Open the app's Location permission page and leave it visible."""
        self._ensure_location_permission_page()

    def _visible(self, locator):
        try:
            return bool(self.driver.find_elements(*locator))
        except Exception:
            return False

    def _ensure_location_permission_page(self):
        """Navigate to the app Location permission page from any Settings page."""
        if self._visible(AndroidSettingsLocators.LOCATION_PERMISSION_TITLE):
            return

        self.adb.shell(
            "am", "start", "-a", "android.settings.APPLICATION_DETAILS_SETTINGS",
            "-d", f"package:{LocationSettings.APP_PACKAGE}",
        )
        time.sleep(2)

        for _ in range(4):
            if self._visible(AndroidSettingsLocators.LOCATION_PERMISSION_TITLE):
                return

            if self._visible(AndroidSettingsLocators.APP_LOCATION_ROW) and (
                self._visible(AndroidSettingsLocators.APP_PERMISSIONS_TITLE)
                or not self._visible(AndroidSettingsLocators.APP_DETAILS_PERMISSIONS)
            ):
                location = self._wait_any(AndroidSettingsLocators.APP_LOCATION_ROW)
                if location is not None:
                    location.click()
                    self._wait_any(AndroidSettingsLocators.LOCATION_PERMISSION_TITLE)
                    if self._visible(AndroidSettingsLocators.LOCATION_PERMISSION_TITLE):
                        return

            if self._visible(AndroidSettingsLocators.APP_DETAILS_PERMISSIONS):
                entry = self._wait_any(AndroidSettingsLocators.APP_DETAILS_PERMISSIONS)
                if entry is not None:
                    entry.click()
                    time.sleep(2)
                    location = self._wait_any(AndroidSettingsLocators.APP_LOCATION_ROW)
                    if location is not None:
                        location.click()
                        self._wait_any(AndroidSettingsLocators.LOCATION_PERMISSION_TITLE)
                        if self._visible(AndroidSettingsLocators.LOCATION_PERMISSION_TITLE):
                            return

            # The Settings task can also be on an unrelated app/permission page.
            self.driver.back()
            time.sleep(1)
            if self._visible(AndroidSettingsLocators.APP_DETAILS_PERMISSIONS):
                continue

        raise AssertionError("Could not open the app Location permission page from Settings")

    # -------------------------------------------------------- system dialogs
    def has_system_location_dialog(self):
        for locator in (
            AndroidSettingsLocators.SYSTEM_ALLOW_FOREGROUND,
            AndroidSettingsLocators.SYSTEM_DENY,
            AndroidSettingsLocators.SYSTEM_DENY_DONT_ASK,
            AndroidSettingsLocators.SYSTEM_ALLOW,
        ):
            if self.driver.find_elements(*locator):
                return True
        return False

    def allow_system_location_dialog(self, one_time=False):
        locator = (
            AndroidSettingsLocators.SYSTEM_ALLOW_ONE_TIME
            if one_time
            else AndroidSettingsLocators.SYSTEM_ALLOW_FOREGROUND
        )
        element = self._wait_any(locator, timeout=8)
        if element is None:
            element = self._wait_any(AndroidSettingsLocators.SYSTEM_ALLOW, timeout=3)
        if element is None:
            return False
        element.click()
        time.sleep(2)
        return True

    def deny_system_location_dialog(self):
        element = self._wait_any(AndroidSettingsLocators.SYSTEM_DENY, timeout=3)
        if element is None:
            element = self._wait_any(AndroidSettingsLocators.SYSTEM_DENY_DONT_ASK, timeout=3)
        if element is None:
            return False
        element.click()
        time.sleep(2)
        return True

    def dismiss_system_dialog(self):
        if self.has_system_location_dialog():
            self.driver.back()
            time.sleep(2)
            return True
        return False

    # -------------------------------------------------------------- network
    def set_airplane_mode(self, enabled: bool):
        state = "enable" if enabled else "disable"
        self.adb.shell("cmd", "connectivity", "airplane-mode", state)
        if not enabled:
            self.adb.shell("svc", "wifi", "enable")
            self.adb.shell("svc", "data", "enable")
        self.wait_for_network(online=not enabled)

    def set_network(self, online: bool):
        self.set_airplane_mode(not online)

    def is_online(self, timeout=5):
        connectivity = self.adb.output("dumpsys", "connectivity", timeout=timeout + 5)
        active = re.search(r"Active default network:\s*(\S+)", connectivity)
        if not active or active.group(1).lower() == "none":
            return False
        ping = self.adb.shell("ping", "-c", "1", "-W", "2", "8.8.8.8", timeout=timeout + 3)
        return ping.returncode == 0

    def wait_for_network(self, online: bool, timeout=None):
        timeout = timeout or LocationSettings.NETWORK_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_online(timeout=3) == online:
                return True
            time.sleep(1)
        return self.is_online(timeout=3) == online

    # ------------------------------------------------------------- settings
    def _wait_any(self, locator, timeout=None):
        try:
            return WebDriverWait(self.driver, timeout or LocationSettings.SETTINGS_TIMEOUT).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException:
            return None

    def _scroll_settings_down(self):
        try:
            self.driver.execute_script(
                "mobile: scrollGesture",
                {
                    "left": 20, "top": 300, "width": 680, "height": 1000,
                    "direction": "down", "percent": 0.8,
                },
            )
            time.sleep(1)
        except Exception:
            pass
