from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time


class WaitHelpers:
    def __init__(self, driver, timeout=20):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def wait_for_element_visible(self, locator, timeout=None):
        if timeout:
            wait = WebDriverWait(self.driver, timeout)
        else:
            wait = self.wait
        return wait.until(EC.visibility_of_element_located(locator))

    def wait_for_element_clickable(self, locator, timeout=None):
        if timeout:
            wait = WebDriverWait(self.driver, timeout)
        else:
            wait = self.wait
        return wait.until(EC.element_to_be_clickable(locator))

    def wait_for_presence(self, locator, timeout=None):
        if timeout:
            wait = WebDriverWait(self.driver, timeout)
        else:
            wait = self.wait
        return wait.until(EC.presence_of_element_located(locator))

    def is_element_present(self, locator, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def wait_for_text(self, locator, text, timeout=None):
        if timeout:
            wait = WebDriverWait(self.driver, timeout)
        else:
            wait = self.wait
        return wait.until(EC.text_to_be_present_in_element(locator, text))
