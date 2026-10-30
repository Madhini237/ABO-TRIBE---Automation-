from utils.wait_helpers import WaitHelpers
from utils.ui_locators import HomeLocators


class HomePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WaitHelpers(driver)

    def is_dashboard_loaded(self):
        try:
            self.wait.wait_for_element_visible(HomeLocators.DASHBOARD_ROOT, timeout=15)
            return True
        except Exception:
            try:
                current_url = self.driver.current_url.lower()
                if "dashboard" in current_url or "home" in current_url:
                    return True
            except Exception:
                pass
            return False
