from appium import webdriver
from appium.options.android import UiAutomator2Options
import os


class DriverSetup:
    @staticmethod
    def get_driver(platform="android", device_name=None, app_package=None, app_activity=None, app_path=None):
        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.device_name = device_name or os.getenv("DEVICE_NAME", "Android")
        options.automation_name = "UiAutomator2"
        options.no_reset = True
        options.new_command_timeout = 300
        options.auto_grant_permissions = True
        options.set_capability('ignoreHiddenApiPolicyError', True)

        if app_package:
            options.app_package = app_package
        if app_activity:
            options.app_activity = app_activity
        if app_path and os.path.exists(app_path):
            options.app = app_path

        # Connect to Appium server
        appium_server_url = os.getenv("APPIUM_SERVER", "http://127.0.0.1:4723")
        driver = webdriver.Remote(appium_server_url, options=options)
        return driver
