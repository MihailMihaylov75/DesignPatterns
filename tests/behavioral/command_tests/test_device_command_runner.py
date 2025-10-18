from behavioral.command.device_command_runner import (
    Device, AtomicCompositeCommand, RetryPolicy,
    ConnectCommand, SetParameterCommand, StartProgramCommand
)


class MyDevice(Device):
    def __init__(self):
        self.connected = False
        self.params = {}
        self.running_program = None
        self.fail_set = False

    def connect(self, timeout_s: int = 5): self.connected = True
    def disconnect(self): self.connected = False

    def set_param(self, k, v):
        if self.fail_set:
            raise RuntimeError("set_param fail")
        prev = self.params.get(k)
        self.params[k] = v
        return prev

    def start_program(self, name): self.running_program = name
    def stop_program(self): self.running_program = None


def test_atomic_setup_success():
    d = MyDevice()
    seq = AtomicCompositeCommand("init", [
        ConnectCommand(d, timeout_s=2, retry_policy=RetryPolicy(max_retries=1)),
        SetParameterCommand(d, "speed", 42),
        StartProgramCommand(d, "Main"),
    ])
    assert seq.run().success is True
    assert d.connected is True
    assert d.params["speed"] == 42
    assert d.running_program == "Main"


def test_atomic_setup_rollback_on_failure():
    d = MyDevice()
    d.fail_set = True
    seq = AtomicCompositeCommand("init", [
        ConnectCommand(d, timeout_s=2),
        SetParameterCommand(d, "speed", 42),
        StartProgramCommand(d, "Main"),
    ])
    res = seq.run()
    assert res.success is False
    # After rollback: either disconnected or still safe to proceed;
    # core expectation: parameter not applied and program not running.
    assert "speed" not in d.params or d.params.get("speed") != 42
    assert d.running_program is None
