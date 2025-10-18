import pytest
from behavioral.chain_of_responsibility.method_chain import build_default_chain, Request, Result


@pytest.mark.unit
def test_authentication_required_but_missing_user_id():
    chain = build_default_chain()
    res = chain.handle(Request(kind="create_order", payload={"requires_auth": True, "items": ["A"]}))
    assert isinstance(res, Result) and res.success is False and "Unauthenticated" in res.message


@pytest.mark.unit
def test_rate_limited_request_is_rejected():
    chain = build_default_chain()
    res = chain.handle(Request(kind="create_order", payload={"user_id": "u1", "rate_limited": True, "items": ["A"]}))
    assert isinstance(res, Result) and res.success is False and "Rate limit" in res.message


@pytest.mark.unit
def test_create_order_validation_passes_with_items():
    chain = build_default_chain()
    res = chain.handle(Request(kind="create_order", payload={"user_id": "u1", "items": ["A", "B"]}))
    assert isinstance(res, Result) and res.success is True and res.data == {"items_count": 2}


@pytest.mark.unit
def test_create_order_validation_fails_when_empty():
    chain = build_default_chain()
    res = chain.handle(Request(kind="create_order", payload={"user_id": "u1", "items": []}))
    assert isinstance(res, Result) and res.success is False and "at least 1 item" in res.message
