# Command Design Pattern Collection

This package provides four practical implementations of the **Command** design pattern, each illustrating a real-world use case:

1. [`text_editor_command.py`](#1-text_editor_commandpy) – user actions with Undo/Redo support.  
2. [`atomic_transfer_command.py`](#2-atomic_transfer_commandpy) – transactional commands with compensating actions.  
3. [`queued_command_bus.py`](#3-queued_command_buspy) – queued command execution with retry and dead-letter handling.  
4. [`device_command_runner.py`](#4-device_command_runnerpy) – device operations with undo, retry, and atomic composite execution.

---

## 1. `text_editor_command.py`

### Purpose
Shows how user actions such as inserting, deleting, or moving text can be modeled as individual commands with `execute()` and `undo()`.  
Ideal for applications requiring **Undo/Redo history** or **macro execution**.

### Key Classes
- `Command` – abstract interface defining `execute()` and `undo()` methods.  
- `TextBuffer` – receiver responsible for holding text and cursor state.  
- `InsertText`, `DeleteText`, `MoveCursor` – concrete command implementations.  
- `MacroCommand` – executes multiple commands atomically.  
- `Invoker` – manages Undo/Redo history stacks.

### Example
```python
from text_editor_command import TextBuffer, InsertText, DeleteText, MoveCursor, Invoker

buf = TextBuffer()
inv = Invoker()

inv.run(InsertText(buf, "Hello "))
inv.run(InsertText(buf, "World"))
inv.run(MoveCursor(buf, 6))
inv.run(InsertText(buf, "dear "))
print(buf.text)  # "Hello dear World"

inv.undo()  # returns "Hello World"
inv.redo()  # returns "Hello dear World"
```

---

## 2. `atomic_transfer_command.py`

### Purpose
Demonstrates an **atomic transactional Command** — a series of actions that either all succeed or are rolled back together if one fails.

### Key Classes
- `Command` – base command class.  
- `AtomicCompositeCommand` – executes subcommands sequentially, rolling back on failure.  
- `BankAccount`, `DepositCommand`, `WithdrawCommand`, `TransferCommand` – example financial domain with compensating logic.  
- `TransactionError` – signals that the composite failed and rolled back.

### Example
```python
from atomic_transfer_command import BankAccount, TransferCommand, TransactionError

source = BankAccount("Alice", balance_cents=10_000)
target = BankAccount("Bob", balance_cents=5_000)

try:
    cmd = TransferCommand(source, target, amount_cents=15_000)
    cmd.execute()
except TransactionError:
    print("Transfer failed and rolled back.")

print(source.balance_cents, target.balance_cents)
# Balances remain unchanged after rollback.
```

---

## 3. `queued_command_bus.py`

### Purpose
Illustrates decoupling between **command producers** and **executors** via a Command Bus and Worker pattern,  
with retry policies and dead-letter management.

### Key Classes
- `Command` – interface for executable tasks.  
- `InMemoryQueue` – minimal FIFO queue with strict error handling.  
- `CommandBus` – enqueues commands for execution.  
- `CommandWorker` – dequeues and executes commands, handles retries and dead-letter cases.  
- `RetryPolicy` and `CommandEnvelope` – encapsulate retry configuration and metadata.  
- `EmailService` and `SendEmailCommand` – example receiver and concrete command.

### Example
```python
from queued_command_bus import (
    InMemoryQueue, CommandBus, CommandWorker, SendEmailCommand, EmailService
)

queue = InMemoryQueue("emails")
bus = CommandBus(queue)
worker = CommandWorker(queue)
service = EmailService()

# Enqueue a command
bus.send(SendEmailCommand(service, "user@example.com", "Test", "Body"))

# Worker processes the queue
processed, failed = worker.drain()
print(f"Processed: {processed}, Dead letters: {failed}")
print(service.outbox)  # [('user@example.com', 'Test', 'Body')]
```

**Advantages:**
- Asynchronous or deferred execution.  
- Automatic retries for transient failures.  
- Centralized logging and fault isolation.

---

## 4. `device_command_runner.py`

### Purpose
Implements a flexible Command framework for **device operations**,  
including connect/disconnect, parameter configuration, start/stop sequences, and atomic transactional workflows.

### Key Classes
- `Device` – abstract interface for a real device (TCP, Modbus, OPC UA, etc.).  
  Must implement:  
  - `connect(timeout_s)`, `disconnect()`  
  - `set_param(key, value)` -> returns previous value for undo  
  - `start_program(name)` and `stop_program()`  
- `Command`, `RetryPolicy`, `CommandResult` – base Command with retry support and results.  
- **Concrete Commands:**  
  - `ConnectCommand`, `DisconnectCommand`  
  - `SetParameterCommand` (restores previous value on undo)  
  - `StartProgramCommand`, `StopProgramCommand` (undo restores previous state)  
- `AtomicCompositeCommand` – executes multiple operations atomically.  
- `DeviceError` and `CommandError` – control operational and transactional errors.

### Example Scenarios

#### ✅ Atomic setup (connect + configure + start)
```python
from device_command_runner import (
    Device, RetryPolicy, AtomicCompositeCommand,
    ConnectCommand, SetParameterCommand, StartProgramCommand
)

class MyDevice(Device):
    def __init__(self):
        self.connected = False
        self.params = {}
        self.running_program = None
    def connect(self, timeout_s: int = 5): self.connected = True
    def disconnect(self): self.connected = False
    def set_param(self, k, v): prev = self.params.get(k); self.params[k] = v; return prev
    def start_program(self, name): self.running_program = name
    def stop_program(self): self.running_program = None

device = MyDevice()
setup = AtomicCompositeCommand(
    "Device initialization",
    [
        ConnectCommand(device, timeout_s=3, retry_policy=RetryPolicy(max_retries=2)),
        SetParameterCommand(device, "cycle_time_ms", 10),
        StartProgramCommand(device, "MainLoop"),
    ],
)

result = setup.run()
if not result.success:
    print("Setup failed and rolled back.")
```

#### Parameter change with rollback
```python
cmd = SetParameterCommand(device, "speed", 42)
res = cmd.run()
# ... testing or calibration ...
if cmd.executed:
    cmd.undo()  # restore previous parameter
```

#### Stop and restore a program
```python
stop_cmd = StopProgramCommand(device)
if stop_cmd.run().success:
    # ... perform maintenance ...
    stop_cmd.undo()  # restore previous running program if available
```

### Benefits and Applications
- Unified command interface for all device types.  
- Supports undo and automatic rollback on failure.  
- Ideal for:  
  - automated system tests and simulations;  
  - configuration sequences (connect -> configure -> start -> stop);  
  - safe parameter updates during runtime.

---

## Summary

| Module | Concept | Key Benefits |
|--------|----------|---------------|
| **text_editor_command** | Undo/Redo, macros, action history | Repeatability, isolation, user control |
| **atomic_transfer_command** | Transactions with compensating actions | All-or-nothing safety, rollback support |
| **queued_command_bus** | Asynchronous command execution via queue | Retry, fault tolerance, scalability |
| **device_command_runner** | Device operation management via commands | Safe execution, undo, retry, atomic setup |
