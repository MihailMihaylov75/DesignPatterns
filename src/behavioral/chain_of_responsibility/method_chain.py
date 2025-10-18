"""
Chain of Responsibility (Behavioral)

Intent:
    Pass a request along a chain of handlers; each handler decides either to
    process the request or to pass it to the next handler.

When to use:
    - Multiple optional processing steps.
    - You want to avoid long if/elif chains.
    - You need to vary or reorder steps at runtime.

Participants:
    - Handler (abstract): declares the interface and keeps a next reference.
    - ConcreteHandler: processes what it is responsible for; otherwise delegates.
    - Client: builds the chain and sends requests.

Notes:
    - Open/Closed: new handlers can be added without modifying existing ones.
    - Keep handlers single-purpose (SRP).
"""

# method_chain.py — Python 3.11-safe forward refs + cleaned docstrings

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class Request:
    """Immutable request object passed through the handler chain.

    :ivar kind: A logical type of the request (e.g., "authenticated_action").
    :ivar payload: Arbitrary request data used by handlers.
    """
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Result:
    """Represents the outcome of handling a request.

    :ivar success: Whether a handler processed the request successfully.
    :ivar message: Short human-readable description.
    :ivar data: Optional data produced by a handler.
    """
    success: bool
    message: str = ""
    data: Optional[Any] = None


class BaseHandler(ABC):
    """Abstract handler defining the chaining protocol.

    Handlers should only implement their responsibility in `handle`.
    Delegation to the next handler is provided via `_delegate`.

    :param next_handler: Optional next handler in the chain.
    """

    def __init__(self, next_handler: Optional["BaseHandler"] = None) -> None:
        self._next: Optional["BaseHandler"] = next_handler

    def set_next(self, handler: "BaseHandler") -> "BaseHandler":
        """Set the next handler in a fluent manner and return it.

        :param handler: The next handler to delegate to.
        :return: The same handler to allow fluent chain building.
        """
        self._next = handler
        return handler

    @abstractmethod
    def handle(self, request: Request) -> Optional[Result]:
        """Attempt to process the request or delegate to the next handler.

        Implementations should:
          1) Check if they are responsible;
          2) Return a Result if handled;
          3) Otherwise delegate via `_delegate`.

        :param request: The incoming request.
        :return: Result if handled; delegated result; or None if unhandled by the chain.
        """
        raise NotImplementedError

    def _delegate(self, request: Request) -> Optional[Result]:
        """Delegate handling to the next handler if present.

        :param request: The incoming request.
        :return: Next handler's result, or None when there is no next handler.
        """
        if self._next is not None:
            return self._next.handle(request)
        return None


class AuthenticationHandler(BaseHandler):
    """Validates that the request is authenticated (e.g., bearer of a user_id)."""

    def handle(self, request: Request) -> Optional[Result]:
        """Process only when authentication is required and present.

        :param request: The incoming request.
        :return: Success result if authenticated; otherwise delegate.
        """
        requires_auth: bool = request.payload.get("requires_auth", False)
        user_id: Optional[str] = request.payload.get("user_id")

        if requires_auth and not user_id:
            return Result(success=False, message="Unauthenticated request")

        # Not applicable or passed → delegate
        return self._delegate(request)


class RateLimitHandler(BaseHandler):
    """Applies a simple rate limiting check using a precomputed flag/counter."""

    def handle(self, request: Request) -> Optional[Result]:
        """Reject the request if rate-limited; otherwise delegate.

        :param request: The incoming request.
        :return: Failure if limited; delegated result otherwise.
        """
        limited: bool = request.payload.get("rate_limited", False)

        if limited:
            return Result(success=False, message="Rate limit exceeded")

        return self._delegate(request)


class BusinessRuleHandler(BaseHandler):
    """Validates a domain-specific business rule for a given request kind."""

    def handle(self, request: Request) -> Optional[Result]:
        """Validate the business rule for supported kinds; otherwise delegate.

        :param request: The incoming request.
        :return: Success if the rule passes; delegated/None otherwise.
        """
        if request.kind == "create_order":
            # Example rule: minimum items required
            items = request.payload.get("items", [])
            if len(items) < 1:
                return Result(success=False, message="Order must contain at least 1 item")
            # Rule passed → considered handled here (no further processing needed)
            return Result(success=True, message="Order validated", data={"items_count": len(items)})

        # Not our responsibility → delegate
        return self._delegate(request)


def build_default_chain() -> BaseHandler:
    """Build a canonical chain (Authentication → RateLimit → BusinessRule).

    :return: The head of the handler chain.
    """
    head = AuthenticationHandler()
    head.set_next(RateLimitHandler()).set_next(BusinessRuleHandler())
    return head


__all__ = [
    "Request",
    "Result",
    "BaseHandler",
    "AuthenticationHandler",
    "RateLimitHandler",
    "BusinessRuleHandler",
    "build_default_chain",
]
