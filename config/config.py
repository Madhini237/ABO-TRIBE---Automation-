import os


class Config:
    # Appium Config
    APPIUM_SERVER = os.getenv("APPIUM_SERVER", "http://localhost:4723")
    PLATFORM_NAME = os.getenv("PLATFORM_NAME", "Android")
    DEVICE_NAME = os.getenv("DEVICE_NAME", "PV5THY65BMNJ957S")
    AUTOMATION_NAME = os.getenv("AUTOMATION_NAME", "UiAutomator2")
    APP_PACKAGE = os.getenv("APP_PACKAGE", "")
    APP_ACTIVITY = os.getenv("APP_ACTIVITY", "")
    NO_RESET = True

    IMPLICIT_WAIT = 10
    EXPLICIT_WAIT = 20

    # Test credentials as per requirement
    VALID_PHONE = "9999999999"
    VALID_OTP = "123456"

    # Timeouts
    PAGE_LOAD_TIMEOUT = 30
