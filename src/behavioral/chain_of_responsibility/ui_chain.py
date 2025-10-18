"""
ui_chain.py — Chain-of-Responsibility for robust UI actions in Selenium tests.

This module defines a small, composable Chain-of-Responsibility (CoR) to perform
UI interactions (e.g., a reliable click) as a sequence of handlers:
FindElement -> EnsureVisible -> ScrollIntoView -> WaitStable -> ClickAction -> ValidateResult.

Each handler either:
  1) handles its responsibility and delegates to the next handler, or
  2) returns a UIResult with an explanatory message.

The flow produces a single, human-readable outcome that is easy to assert in tests.
"""

from dataclasses import dataclass
from typing import Any, Optional, Mapping
from types import MappingProxyType
from abc import ABC, abstractmethod

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ---------- Data Models ----------
@dataclass(frozen=True, slots=True)
class UIRequest:
    """
    Encapsulates the input for a UI action flow.

    :param driver: Selenium WebDriver instance used to interact with the page.
    :param by: Locator strategy as string (e.g., By.CSS_SELECTOR -> a string constant).
    :param value: Locator value corresponding to the strategy.
    :param action: Logical action to perform ("click", ...). Handlers may ignore unknown actions.
    :param params: Extra parameters for fine-grained control (e.g., timeouts, validation locators).
                   Must behave like a read-only mapping; defaults to an empty immutable mapping.
    """
    driver: WebDriver
    by: str
    value: str
    action: str = "click"
    params: Mapping[str, Any] = MappingProxyType({})


@dataclass(slots=True)
class UIResult:
    """
    Represents the outcome of a UI flow.

    :param success: Whether the flow succeeded.
    :param message: Short human-readable description of the outcome.
    :param data: Optional additional payload (e.g., diagnostics).
    """
    success: bool
    message: str = ""
    data: Optional[Any] = None


# ---------- Chain Base ----------
class UIHandler(ABC):
    """
    Abstract base handler for the UI Chain-of-Responsibility.

    A handler should:
      - Implement a single responsibility in `handle`.
      - Delegate to the next handler when appropriate via `_delegate`.
      - Return a `UIResult` when it fully decides the outcome (success/failure).

    Handlers are designed to be stateless; inject dependencies via `__init__` if needed.
    """

    def __init__(self, nxt: Optional["UIHandler"] = None) -> None:
        """
        Initializes a handler with an optional next handler.

        :param nxt: Next handler in the chain to which this handler can delegate.
        """
        self._next = nxt

    def set_next(self, nxt: "UIHandler") -> "UIHandler":
        """
        Sets the next handler and returns it to allow fluent chain construction.

        :param nxt: Next handler in the chain.
        :return: The provided handler, enabling chained `set_next(...)` calls.
        """
        self._next = nxt
        return nxt

    def _delegate(self, req: UIRequest) -> Optional[UIResult]:
        """
        Delegates processing to the next handler in the chain, if any.

        :param req: The UI request being processed.
        :return: The next handler's result, or None if there is no next handler.
        """
        return self._next.handle(req) if self._next else None

    @abstractmethod
    def handle(self, req: UIRequest) -> Optional[UIResult]:
        """
        Attempts to process the request or delegate further.

        :param req: The UI request being processed.
        :return: A `UIResult` if the handler decides the outcome; otherwise, the delegated result;
                 or None when the chain ends without a decision.
        """
        raise NotImplementedError


# ---------- Concrete Handlers ----------
class FindElement(UIHandler):
    """
    Waits until the element is present in the DOM.

    Responsibility:
      - Ensures the target element exists in the DOM before proceeding.

    Parameters (via `req.params`):
      - timeout_present (int): Max seconds to wait for presence (default: 8).
    """

    def handle(self, req: UIRequest) -> Optional[UIResult]:
        """
        Waits for element presence and delegates on success.

        :param req: UIRequest containing driver and locator.
        :return: Failure result if presence is not achieved; delegated result otherwise.
        """
        timeout = int(req.params.get("timeout_present", 8))
        try:
            WebDriverWait(req.driver, timeout).until(
                EC.presence_of_element_located((req.by, req.value))
            )
            return self._delegate(req)
        except Exception:
            return UIResult(False, f"Element not present: ({req.by}, {req.value})")


class EnsureVisible(UIHandler):
    """
    Waits until the element is visible to the user.

    Responsibility:
      - Ensures the element has non-zero size and is not hidden, preventing interaction errors.

    Parameters (via `req.params`):
      - timeout_visible (int): Max seconds to wait for visibility (default: 8).
    """

    def handle(self, req: UIRequest) -> Optional[UIResult]:
        """
        Waits for element visibility and delegates on success.

        :param req: UIRequest containing driver and locator.
        :return: Failure result if visibility is not achieved; delegated result otherwise.
        """
        timeout = int(req.params.get("timeout_visible", 8))
        try:
            WebDriverWait(req.driver, timeout).until(
                EC.visibility_of_element_located((req.by, req.value))
            )
            return self._delegate(req)
        except Exception:
            return UIResult(False, f"Element not visible: ({req.by}, {req.value})")


class ScrollIntoView(UIHandler):
    """
    Scrolls the element into the viewport.

    Responsibility:
      - Brings off-screen elements into view, reducing click interception by fixed headers/footers.
    """

    def handle(self, req: UIRequest) -> Optional[UIResult]:
        """
        Scrolls the target element into the center of the viewport and delegates.

        :param req: UIRequest containing driver and locator.
        :return: Failure result on script/find errors; delegated result otherwise.
        """
        try:
            el = req.driver.find_element(req.by, req.value)
            req.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            return self._delegate(req)
        except Exception:
            return UIResult(False, "Failed to scroll element into view")


class WaitStable(UIHandler):
    """
    Waits for the element's layout to stabilize.

    Responsibility:
      - Mitigates flakiness caused by animations/layout shifts just before interaction.

    Parameters (via `req.params`):
      - stability_delay (float): Seconds between two rect samples (default: 0.25).
    """

    def handle(self, req: UIRequest) -> Optional[UIResult]:
        """
        Samples the element's boundingClientRect twice and compares results.

        :param req: UIRequest containing driver and locator.
        :return: Failure if positions differ (unstable layout); delegated result otherwise.
        """
        import time
        js = "return arguments[0].getBoundingClientRect().toJSON();"
        try:
            el = req.driver.find_element(req.by, req.value)
            rect1 = req.driver.execute_script(js, el)
            time.sleep(float(req.params.get("stability_delay", 0.25)))
            rect2 = req.driver.execute_script(js, el)
            if rect1 == rect2:
                return self._delegate(req)
            return UIResult(False, "Element layout unstable before action")
        except Exception:
            return UIResult(False, "Failed stability check")


class ClickAction(UIHandler):
    """
    Performs the requested action (demo: `click`).

    Responsibility:
      - Executes the primary UI action once preconditions are met.

    Notes:
      - If `req.action` is not "click", this handler delegates without acting.
    """

    def handle(self, req: UIRequest) -> Optional[UIResult]:
        """
        Clicks the target element when `req.action == "click"`.

        :param req: UIRequest containing driver, locator, and action.
        :return: Failure if the click cannot be performed; otherwise, the delegated result
                 (or success if this is the terminal handler).
        """
        if req.action != "click":
            return self._delegate(req)  # Not our responsibility -> pass it on

        try:
            el = req.driver.find_element(req.by, req.value)
            el.click()
            # Propagate further if something else (e.g., validation) needs to run.
            return self._delegate(req) or UIResult(True, "Clicked")
        except Exception:
            return UIResult(False, "Click failed")


class ValidateResult(UIHandler):
    """
    Validates a post-condition after the action.

    Responsibility:
      - Confirms expected UI feedback (e.g., toast, label change) to deem the flow successful.

    Parameters (via `req.params`):
      - validate_locator (tuple[str, str]): Locator (by, value) for the expected element.
      - timeout_validate (int): Max seconds to wait for validation (default: 6).
    """

    def handle(self, req: UIRequest) -> Optional[UIResult]:
        """
        Performs a simple post-condition validation if requested.

        :param req: UIRequest containing optional validation parameters.
        :return: Success if the validation element appears; failure if it does not within timeout;
                 success with a neutral message when no validation is requested.
        """
        validate = req.params.get("validate_locator")
        if validate:
            by2, val2 = validate  # both should be str
            timeout = int(req.params.get("timeout_validate", 6))
            try:
                WebDriverWait(req.driver, timeout).until(
                    EC.visibility_of_element_located((by2, val2))
                )
                return UIResult(True, "Validation passed")
            except Exception:
                return UIResult(False, f"Validation not met: ({by2}, {val2})")
        return UIResult(True, "No validation requested")


# ---------- Builder ----------
def build_ui_click_flow() -> UIHandler:
    """
    Builds a canonical chain for robust clicking in UI tests.

    Flow:
      1) FindElement       — wait for DOM presence.
      2) EnsureVisible     — wait for visibility.
      3) ScrollIntoView    — center in viewport.
      4) WaitStable        — ensure layout stability.
      5) ClickAction       — perform the click.
      6) ValidateResult    — optional post-condition check.

    :return: The head of the chain (first handler).
    """
    head = FindElement()
    head.set_next(EnsureVisible()) \
        .set_next(ScrollIntoView()) \
        .set_next(WaitStable()) \
        .set_next(ClickAction()) \
        .set_next(ValidateResult())
    return head
