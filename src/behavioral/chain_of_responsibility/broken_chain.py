"""
broken_chain.py — Event-broker/Observer flavored Chain-of-Responsibility demo.

This example wires a lightweight in-process event bus (Game.queries) where
'modifiers' subscribe and adjust a Query in response to creature attribute lookups.
It demonstrates a responsibility chain realized via observers that may mutate the
Query (attack/defense) and then let others continue.
"""

from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Any


# ------------------------------- Domain --------------------------------- #
class WhatToQuery(Enum):
    """Kinds of attributes that can be requested for a creature."""
    ATTACK = auto()
    DEFENSE = auto()


@dataclass(slots=True)
class Query:
    """
    Mutable message passed through the chain of observers.

    :param creature_name: Name of the creature whose attribute is requested.
    :param what_to_query: Attribute kind (attack/defense).
    :param value: Current value (starts with a default, observers may modify).
    """
    creature_name: str
    what_to_query: WhatToQuery
    value: int


class Event:
    """
    Simple synchronous pub-sub list with call semantics.

    Subscribers are callables of signature: (sender: Any, query: Query) -> None.

    Usage:
        event.append(handler)
        event(sender, query)  # dispatches to all subscribers in order
        event.remove(handler)

    Notes:
    - Handlers can mutate `query.value` to influence the final result.
    """

    def __init__(self) -> None:
        self._subscribers: List[Callable[[Any, Query], None]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """Dispatches the event to all subscribers in registration order."""
        for fn in list(self._subscribers):
            fn(*args, **kwargs)

    def append(self, fn: Callable[[Any, Query], None]) -> None:
        """Registers a handler."""
        self._subscribers.append(fn)

    def remove(self, fn: Callable[[Any, Query], None]) -> None:
        """Unregisters a handler if present."""
        try:
            self._subscribers.remove(fn)
        except ValueError:
            pass  # idempotent remove


class Game:
    """
    Coordinates query dispatch to observers (modifiers).

    :ivar queries: Event used to broadcast Query objects to all subscribers.
    """

    def __init__(self) -> None:
        self.queries = Event()

    def perform_query(self, sender: Any, query: Query) -> None:
        """
        Broadcasts a Query to all current subscribers.

        :param sender: The originator of the query (typically a Creature).
        :param query: The mutable Query to be processed by modifiers.
        """
        self.queries(sender, query)


class Creature:
    """
    Creature with base (initial) stats influenced by active modifiers.

    :param game: Game instance providing the event bus.
    :param name: Creature name.
    :param attack: Base attack value.
    :param defense: Base defense value.
    """

    def __init__(self, game: Game, name: str, attack: int, defense: int) -> None:
        self.game = game
        self.name = name
        self.initial_attack = attack
        self.initial_defense = defense

    @property
    def attack(self) -> int:
        """
        Computes effective attack via the event chain.

        :return: Final attack after modifiers adjust the Query.
        """
        q = Query(self.name, WhatToQuery.ATTACK, self.initial_attack)
        self.game.perform_query(self, q)
        return q.value

    @property
    def defense(self) -> int:
        """
        Computes effective defense via the event chain.

        :return: Final defense after modifiers adjust the Query.
        """
        q = Query(self.name, WhatToQuery.DEFENSE, self.initial_defense)  # FIXED
        self.game.perform_query(self, q)
        return q.value

    def __str__(self) -> str:
        """Human-readable representation: '<name> (attack/defense)'."""
        return f"{self.name} ({self.attack}/{self.defense})"


# --------------------------- Responsibility Chain ----------------------- #
class CreatureModifier(ABC):
    """
    Base class for modifiers that participate in the responsibility chain.

    Registers `self.handle` to the game's event bus and supports context-manager
    lifetime for automatic unsubscribe.

    :param game: Game instance to subscribe to.
    :param creature: Target creature this modifier affects.
    """

    def __init__(self, game: Game, creature: Creature) -> None:
        self.game = game
        self.creature = creature
        self.game.queries.append(self.handle)

    def handle(self, sender: Any, query: Query) -> None:
        """
        Observes the Query and may mutate `query.value` if applicable.

        :param sender: The originator of the query (Creature).
        :param query: Mutable Query to inspect and possibly modify.
        """
        # Default no-op; concrete modifiers override.
        return None

    # Context management for scoped subscription
    def __enter__(self) -> "CreatureModifier":
        """Enters a scoped subscription (no-op; returns self)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Unsubscribes the handler when leaving the context."""
        self.game.queries.remove(self.handle)


class DoubleAttackModifier(CreatureModifier):
    """
    Doubles attack for the target creature while the modifier is active.
    """

    def handle(self, sender: Any, query: Query) -> None:
        """
        Doubles `query.value` when the sender & attribute match.

        :param sender: The originator of the query (Creature).
        :param query: Query with current value to potentially modify.
        """
        if sender is self.creature and query.what_to_query == WhatToQuery.ATTACK:
            query.value *= 2


class IncreaseDefenseModifier(CreatureModifier):
    """
    Increases defense by a flat amount for the target creature while active.

    The increment is +3 (demo constant).
    """

    def handle(self, sender: Any, query: Query) -> None:
        """
        Adds +3 to `query.value` when the sender & attribute match.

        :param sender: The originator of the query (Creature).
        :param query: Query with current value to potentially modify.
        """
        if sender is self.creature and query.what_to_query == WhatToQuery.DEFENSE:
            query.value += 3


# ------------------------------- Demo ----------------------------------- #
if __name__ == "__main__":
    game = Game()
    goblin = Creature(game, "Strong Goblin", attack=2, defense=2)
    print(goblin)  # baseline

    with DoubleAttackModifier(game, goblin):
        print(goblin)  # attack doubled
        with IncreaseDefenseModifier(game, goblin):
            print(goblin)  # attack doubled, defense +3

    print(goblin)  # back to baseline
