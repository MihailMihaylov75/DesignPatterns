from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


# ==========================
# Module: text_editor_command
# Purpose: Encapsulate user actions as Commands with Undo/Redo and Macro support.
# ==========================


class Command(ABC):
    """
    Base interface for executable actions with undo support.

    :param description: Human-readable description of the command.
    """

    def __init__(self, description: str) -> None:
        self._description = description

    @property
    def description(self) -> str:
        """
        Returns a short, human-readable description of the command.

        :return: Command description string.
        """
        return self._description

    @abstractmethod
    def execute(self) -> None:
        """
        Executes the command.
        """

    @abstractmethod
    def undo(self) -> None:
        """
        Reverts the effects of execute().
        """


@dataclass
class TextBuffer:
    """
    Simple text receiver to demonstrate editor-like operations.
    """
    text: str = ""
    cursor: int = 0

    def insert(self, s: str) -> None:
        """
        Inserts string at the current cursor and moves the cursor forward.

        :param s: Text to insert.
        """
        self.text = self.text[: self.cursor] + s + self.text[self.cursor:]
        self.cursor += len(s)

    def delete(self, count: int) -> str:
        """
        Deletes `count` characters starting at current cursor.

        :param count: Number of characters to delete.
        :return: The deleted substring (for undo).
        """
        deleted = self.text[self.cursor: self.cursor + count]
        self.text = self.text[: self.cursor] + self.text[self.cursor + count:]
        return deleted

    def move_cursor(self, pos: int) -> int:
        """
        Moves cursor to `pos` within [0, len(text)].

        :param pos: Target position.
        :return: Previous cursor position (for undo).
        """
        pos = max(0, min(pos, len(self.text)))
        prev = self.cursor
        self.cursor = pos
        return prev


class InsertText(Command):
    """
    Inserts text at the current cursor.
    """

    def __init__(self, buffer: TextBuffer, text: str) -> None:
        super().__init__(description=f"Insert '{text}'")
        self._buffer = buffer
        self._text = text
        self._start_pos: Optional[int] = None

    def execute(self) -> None:
        """Insert and remember start position for undo."""
        self._start_pos = self._buffer.cursor
        self._buffer.insert(self._text)

    def undo(self) -> None:
        """Restore buffer by deleting the inserted slice."""
        if self._start_pos is None:
            return
        prev = self._buffer.move_cursor(self._start_pos)
        _ = prev  # explicit no-op to satisfy linters about unused variable
        self._buffer.delete(len(self._text))


class DeleteText(Command):
    """
    Deletes `count` characters at the current cursor.
    """

    def __init__(self, buffer: TextBuffer, count: int) -> None:
        super().__init__(description=f"Delete {count} chars")
        self._buffer = buffer
        self._count = max(0, count)
        self._deleted: str = ""

    def execute(self) -> None:
        """Delete and remember removed text for undo."""
        self._deleted = self._buffer.delete(self._count)

    def undo(self) -> None:
        """Reinsert the previously deleted text."""
        self._buffer.insert(self._deleted)


class MoveCursor(Command):
    """
    Moves the cursor to an absolute position.
    """

    def __init__(self, buffer: TextBuffer, position: int) -> None:
        super().__init__(description=f"Move cursor to {position}")
        self._buffer = buffer
        self._target = position
        self._prev: Optional[int] = None

    def execute(self) -> None:
        """Move and remember previous position for undo."""
        self._prev = self._buffer.move_cursor(self._target)

    def undo(self) -> None:
        """Return cursor to the previous position."""
        if self._prev is None:
            return
        _ = self._buffer.move_cursor(self._prev)


class MacroCommand(Command):
    """
    Executes a list of commands atomically (best-effort) with reverse-order undo.

    :param items: Ordered list of commands to execute.
    """

    def __init__(self, items: Optional[List[Command]] = None) -> None:
        super().__init__(description="Macro")
        self._items: List[Command] = list(items) if items else []
        self._executed: int = 0

    def add(self, cmd: Command) -> None:
        """
        Appends a command to the macro.

        :param cmd: Command to add.
        """
        self._items.append(cmd)

    def execute(self) -> None:
        """Execute each command in order; remember how many succeeded."""
        self._executed = 0
        for cmd in self._items:
            cmd.execute()
            self._executed += 1

    def undo(self) -> None:
        """Undo in reverse order only the commands that were executed."""
        for cmd in reversed(self._items[: self._executed]):
            cmd.undo()
        self._executed = 0


class Invoker:
    """
    Executes commands and maintains undo/redo history.

    :param undo_limit: Maximum number of entries kept in history.
    """

    def __init__(self, undo_limit: int = 100) -> None:
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._undo_limit = max(1, undo_limit)

    def run(self, cmd: Command) -> None:
        """
        Executes a command and records it for undo; clears redo history.

        :param cmd: Command to execute.
        """
        cmd.execute()
        self._undo_stack.append(cmd)
        if len(self._undo_stack) > self._undo_limit:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> bool:
        """
        Undoes the last executed command, if any.

        :return: True if a command was undone; False otherwise.
        """
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        return True

    def redo(self) -> bool:
        """
        Re-executes the last undone command, if any.

        :return: True if a command was redone; False otherwise.
        """
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        return True
