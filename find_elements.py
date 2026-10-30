from appium import webdriver
from appium.options.android import UiAutomator2Options
opts = UiAutomator2Options()
opts.platform_name='Android'
opts.device_name='PV5THY65BMNJ957S'
opts.automation_name='UiAutomator2'
opts.no_reset=True
opts.auto_grant_permissions=True
opts.set_capability('ignoreHiddenApiPolicyError', True)
d = webdriver.Remote('http://127.0.0.1:4723', options=opts)
elems = d.find_elements('xpath', '//*[@clickable="true" or @focusable="true"]')
for i,e in enumerate(elems):
    try:
        print(i, e.tag_name, '|text:', e.get_attribute('text'), '|desc:', e.get_attribute('content-desc'), '|rid:', e.get_attribute('resource-id'), '|hint:', e.get_attribute('hint'))
    except Exception:
        pass
d.quit()
