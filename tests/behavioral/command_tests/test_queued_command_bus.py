from behavioral.command.queued_command_bus import InMemoryQueue, CommandBus, CommandWorker, Command,\
    RetryPolicy, EmailService, SendEmailCommand


class AlwaysFail(Command):
    def __init__(self): super().__init__("AlwaysFail")
    def execute(self): raise RuntimeError("boom")


def test_queue_success_path():
    # Use built-in SendEmailCommand via small local
    q = InMemoryQueue("q")
    bus = CommandBus(q)
    worker = CommandWorker(q)
    svc = EmailService()
    bus.send(SendEmailCommand(svc, "u@example.com", "S", "B"))
    processed, dead = worker.drain()
    assert processed >= 1
    assert dead == 0
    assert ("u@example.com", "S", "B") in svc.outbox


def test_queue_dead_letter_on_retries_exhausted():
    q = InMemoryQueue("q")
    bus = CommandBus(q)
    worker = CommandWorker(q)
    bus.send(AlwaysFail(), retry_policy=RetryPolicy(max_retries=1))
    processed, dead = worker.drain(max_steps=10)
    assert dead == 1
