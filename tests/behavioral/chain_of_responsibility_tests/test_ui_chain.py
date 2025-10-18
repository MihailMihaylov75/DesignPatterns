import pytest
from behavioral.chain_of_responsibility import ui_chain as UIC


class DummyElement:
    def __init__(self):
        self._clicked = False
        self._rect = {"x": 10, "y": 10, "width": 100, "height": 40}

    def click(self):
        self._clicked = True


class FakeDriver:
    def __init__(self):
        self.element = DummyElement()

    def find_element(self, by, value):
        return self.element

    def execute_script(self, script, element):
        return dict(self.element._rect)


class FakeWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, condition):
        # Does not call condition; directly declares success
        return True


@pytest.mark.unit
def test_ui_click_flow_happy_path(monkeypatch):
    # We patch only WebDriverWait; we leave EC real and callable
    monkeypatch.setattr(UIC, "WebDriverWait", FakeWait)

    driver = FakeDriver()
    flow = UIC.build_ui_click_flow()
    req = UIC.UIRequest(
        driver=driver,
        by="css selector",
        value="#add-btn",
        action="click",
        params={"validate_locator": ("css selector", "#toast-success")},
    )
    result = flow.handle(req)
    assert result and result.success, result.message
