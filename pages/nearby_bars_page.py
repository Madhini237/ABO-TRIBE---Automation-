import re
import time
import xml.etree.ElementTree as ET

from config.settings import LocationSettings
from utils.ui_locators import HomeLocators, LocationLocators, NearbyBarsLocators

DISTANCE_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>m|km)\s*[•·]\s*(?P<city>.+)$")


class NearbyBarsPage:
    """Reads the eligible bars list below Most Visited on the home screen."""

    def __init__(self, driver):
        self.driver = driver

    # --------------------------------------------------------------- scroll
    def _scroll(self, direction="down", percent=0.75):
        self.driver.execute_script(
            "mobile: scrollGesture",
            {
                "left": 24, "top": 260, "width": 672, "height": 1000,
                "direction": direction, "percent": percent,
            },
        )

    def scroll_to_top(self):
        """Return to the top of the home feed without triggering pull-to-refresh."""
        for _ in range(4):
            self.dismiss_blocking_dialogs()
            if self._home_header_visible():
                return
            self._scroll(direction="up", percent=0.9)
            time.sleep(0.4)

    def _home_header_visible(self):
        for element in self.driver.find_elements(
            "xpath", "//*[@clickable='true' and @content-desc!='']"
        ):
            raw = (element.get_attribute("content-desc") or "").strip()
            if "\n" not in raw or raw.lower().startswith("search for") or "•" in raw:
                continue
            bounds = element.get_attribute("bounds") or ""
            match = re.match(r"\[\d+,(\d+)\]", bounds)
            if match and int(match.group(1)) <= 180:
                return True
        return False

    def dismiss_blocking_dialogs(self):
        if self.driver.find_elements(*LocationLocators.LOCATION_ERROR_TITLE):
            cancel = self.driver.find_elements(
                "xpath", "//*[@content-desc='Cancel' or @text='Cancel']"
            )
            if cancel:
                cancel[0].click()
            else:
                self.driver.back()
            time.sleep(1)
            return True
        if self.driver.find_elements(*LocationLocators.PRIMER_NOT_NOW):
            self.driver.find_elements(*LocationLocators.PRIMER_NOT_NOW)[0].click()
            time.sleep(1)
            return True
        return False

    def scroll_down(self):
        self._scroll(direction="down", percent=0.75)
        time.sleep(1)

    # ---------------------------------------------------------------- parse
    def _page_root(self):
        try:
            return ET.fromstring(self.driver.page_source)
        except ET.ParseError:
            return None

    @staticmethod
    def _bounds(node):
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
        if not match:
            return None
        return tuple(int(match.group(index)) for index in range(1, 5))

    @classmethod
    def _find_heading(cls, root):
        for node in root.iter():
            label = (node.attrib.get("content-desc") or "") + " " + (
                node.attrib.get("text") or ""
            )
            if "nearby bars" in label.lower():
                bounds = cls._bounds(node)
                if bounds:
                    return bounds
        return None

    @classmethod
    def _parse_card(cls, node):
        raw = (node.attrib.get("content-desc") or "").strip()
        if "•" not in raw and "·" not in raw:
            return None

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        distance_index = None
        distance_match = None
        for index, line in enumerate(lines):
            match = DISTANCE_PATTERN.match(line)
            if match:
                distance_index = index
                distance_match = match
                break
        if distance_index is None or distance_index == 0:
            return None

        name_lines = lines[:distance_index]
        name = name_lines[-1]
        if re.fullmatch(r"\d+(?:\.\d+)?", name) and len(name_lines) >= 2:
            name = name_lines[-2]

        rating = None
        for line in reversed(name_lines[:-1]):
            if re.fullmatch(r"\d+(?:\.\d+)?", line):
                rating = float(line)
                break

        value = float(distance_match.group("value"))
        unit = distance_match.group("unit").lower()
        meters = value if unit == "m" else value * 1000

        return {
            "raw": raw,
            "name": name,
            "rating": rating,
            "distance_text": f"{distance_match.group('value')} {unit}",
            "meters": meters,
            "city": distance_match.group("city").strip(),
            "bounds": cls._bounds(node),
        }

    def _cards_at_current_position(self, seen_heading):
        self.dismiss_blocking_dialogs()
        root = self._page_root()
        if root is None:
            return [], seen_heading

        heading_bounds = self._find_heading(root)
        if heading_bounds:
            seen_heading = True

        cards = []
        for node in root.iter():
            bounds = self._bounds(node)
            if bounds is None:
                continue
            card = self._parse_card(node)
            if card is None:
                continue
            if heading_bounds:
                # Ignore Top Picks cards above the Nearby Bars heading.
                if bounds[1] < heading_bounds[3]:
                    continue
            elif not seen_heading:
                continue
            cards.append(card)
        return cards, seen_heading

    # ------------------------------------------------------------- collect
    def collect_nearby_bars(self, max_scrolls=None):
        """Scroll the home page and return the unique Nearby Bars cards."""
        max_scrolls = max_scrolls or LocationSettings.MAX_SCROLLS
        self.dismiss_blocking_dialogs()

        # Start in the correct section. At the very top the Top Picks cards are
        # visible, so they must be ignored until the Nearby Bars heading is
        # reached. If the feed is already scrolled past the heading, all visible
        # bar cards belong to the nearby list.
        seen_heading = self._below_nearby_heading()

        collected = {}
        empty_rounds = 0

        for _ in range(max_scrolls):
            cards, seen_heading = self._cards_at_current_position(seen_heading)
            new_cards = 0
            for card in cards:
                key = (card["name"].lower(), card["city"].lower(), card["distance_text"])
                if key not in collected:
                    collected[key] = card
                    new_cards += 1

            if new_cards:
                empty_rounds = 0
            else:
                empty_rounds += 1
                if seen_heading and empty_rounds >= 2:
                    break
            self.scroll_down()

        return list(collected.values())

    def _below_nearby_heading(self):
        top_markers = self.driver.find_elements(
            "xpath",
            "//*[contains(@content-desc,'Most Visited') or contains(@content-desc,'TOP PICKS')]",
        )
        if top_markers:
            return False
        return bool(self.driver.find_elements(*NearbyBarsLocators.BAR_CARD))

    def wait_for_nearby_bars(self, timeout=None, max_scrolls=None):
        timeout = timeout or LocationSettings.BARS_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.has_empty_state() or self.has_error_state():
                return []
            cards = self.collect_nearby_bars(max_scrolls=max_scrolls)
            if cards:
                return cards
            time.sleep(1)
        return []

    def wait_for_any_bars_state(self, timeout=None, max_scrolls=None):
        """Return ('bars', cards) / ('empty', []) / ('error', []) / ('timeout', [])."""
        timeout = timeout or LocationSettings.BARS_TIMEOUT
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            cards = self.collect_nearby_bars(max_scrolls=max_scrolls)
            if cards:
                return "bars", cards
            if self.has_empty_state():
                return "empty", []
            if self.has_error_state() or self.is_offline_banner_visible():
                return "error", []
            time.sleep(1)
        return "timeout", []

    # ------------------------------------------------------------- states
    def is_nearby_heading_visible(self):
        return bool(self.driver.find_elements(*HomeLocators.NEARBY_BARS_HEADING))

    def is_offline_banner_visible(self):
        return bool(self.driver.find_elements(*NearbyBarsLocators.OFFLINE_BANNER))

    def is_retry_visible(self):
        return bool(self.driver.find_elements(*NearbyBarsLocators.RETRY))

    def click_retry(self):
        buttons = self.driver.find_elements(*NearbyBarsLocators.RETRY)
        if not buttons:
            return False
        buttons[0].click()
        time.sleep(2)
        return True

    def has_empty_state(self):
        return bool(self.driver.find_elements(*NearbyBarsLocators.EMPTY_STATE))

    def has_error_state(self):
        return bool(self.driver.find_elements(*NearbyBarsLocators.ERROR_STATE))

    def page_text(self):
        return self.driver.page_source.lower()

    # ------------------------------------------------------------- helpers
    @staticmethod
    def distances_ascending(cards):
        values = [card["meters"] for card in cards]
        return values == sorted(values)

    @staticmethod
    def distances(cards):
        return [card["meters"] for card in cards]

    @staticmethod
    def names(cards):
        return [card["name"] for card in cards]

    @staticmethod
    def cities(cards):
        return sorted({card["city"] for card in cards})

    def assert_distances_are_valid(self, cards):
        assert cards, "No eligible nearby bars were returned"
        for card in cards:
            assert card["name"], f"Bar card has no name: {card['raw']!r}"
            assert card["meters"] >= 0, f"Invalid distance on bar card: {card['raw']!r}"
            assert card["city"], f"Bar card has no city: {card['raw']!r}"
