
from appium import webdriver
from appium.options.android import UiAutomator2Options
import xml.etree.ElementTree as ET
import os
import re

# Configure your connected Android device
options = UiAutomator2Options()
options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.device_name = "Android Device"

# Replace with your actual device ID if necessary
options.udid = "PV5THY65BMNJ957S"

options.no_reset = True
options.set_capability(
    "appium:ignoreHiddenApiPolicyError",
    True
)

driver = None

try:
    # Connect to Appium
    driver = webdriver.Remote(
        "http://127.0.0.1:4723",
        options=options
    )

    print("\n========== DEVICE INFORMATION ==========")
    print("Device:", driver.capabilities.get("deviceName"))
    print("Package:", driver.current_package)
    print("Activity:", driver.current_activity)

    # Retrieve the complete UI hierarchy
    source = driver.page_source

    # Save the hierarchy for later inspection
    with open("screen_hierarchy.xml", "w", encoding="utf-8") as file:
        file.write(source)

    print("\nUI hierarchy saved to screen_hierarchy.xml")

    # Parse the XML
    root = ET.fromstring(source)

    print("\n========== DISCOVERED UI ELEMENTS ==========\n")

    for index, element in enumerate(root.iter(), start=1):

        attrs = element.attrib

        resource_id = attrs.get("resource-id", "")
        text = attrs.get("text", "")
        content_desc = attrs.get("content-desc", "")
        class_name = attrs.get("class", "")
        clickable = attrs.get("clickable", "")
        enabled = attrs.get("enabled", "")
        bounds = attrs.get("bounds", "")

        # Show elements likely to be relevant to automation
        if (
            resource_id
            or text
            or content_desc
            or class_name.endswith(("EditText", "Button"))
            or clickable == "true"
        ):
            print(f"\nElement {index}")
            print("  Class       :", class_name)
            print("  Resource ID :", resource_id)
            print("  Text        :", text)
            print("  Content Desc:", content_desc)
            print("  Clickable   :", clickable)
            print("  Enabled     :", enabled)
            print("  Bounds      :", bounds)

            # Suggest a locator where possible
            if resource_id:
                print(
                    "  Suggested locator: "
                    f"(AppiumBy.ID, {resource_id!r})"
                )
            elif content_desc:
                print(
                    "  Suggested locator: "
                    f"(AppiumBy.ACCESSIBILITY_ID, {content_desc!r})"
                )
            elif text:
                print(
                    "  Suggested locator: "
                    f"(AppiumBy.XPATH, "
                    f"//*[@text={text!r}])"
                )

    print("\n========== INSPECTION COMPLETE ==========")

except Exception as error:
    print("\nInspection failed:", str(error))

finally:
    if driver:
        driver.quit()
