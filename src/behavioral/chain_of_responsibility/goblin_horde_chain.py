# goblin_horde_chain.py
"""
Event-driven chain-of-responsibility demo with Goblins.

The pattern here is implemented via an in-process "event chain":
each creature can observe queries for ATTACK/DEFENSE and adjust
the queried value for others in the same Game (horde).

Python 3.11+.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List


# ----------------------------- Domain ----------------------------------- #
class WhatToQuery(Enum):
    """Kinds of attributes that can be requested for a creature."""
    ATTACK = auto()
    DEFENSE = auto()


@dataclass(slots=True)
class Query:
    """
    Mutable message passed through the chain of observers.

    :param what_to_query: Attribute kind being queried (attack/defense).
    :param value: Current numeric value; observers can modify in place.
    """
    what_to_query: WhatToQuery
    value: int


class Game:
    """
    Container for all creatures participating in the event chain.

    :ivar creatures: The roster of creatures in the "horde".
    """

    def __init__(self) -> None:
        self.creatures: List["Creature"] = []


class Creature(ABC):
    """
    Abstract base creature with initial (base) stats.

    :param game: Game instance that hosts this creature.
    :param attack: Base attack value.
    :param defense: Base defense value.
    """

    def __init__(self, game: Game, attack: int, defense: int) -> None:
        self.game = game
        self.initial_attack = attack
        self.initial_defense = defense

    @property
    @abstractmethod
    def attack(self) -> int:
        """
        Computes the *effective* attack, factoring in the event chain.

        :return: Final attack after modifiers from other creatures.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def defense(self) -> int:
        """
        Computes the *effective* defense, factoring in the event chain.

        :return: Final defense after modifiers from other creatures.
        """
        raise NotImplementedError

    @abstractmethod
    def query(self, source: "Creature", query: Query) -> None:
        """
        Observes a Query and may adjust its value if applicable.

        :param source: The creature whose attribute is being queried.
        :param query: The mutable Query message (kind + value).
        """
        raise NotImplementedError


# ------------------------- Concrete Creatures ---------------------------- #
class Goblin(Creature):
    """
    Basic Goblin.

    Rules:
      - Each *other* Goblin adds +1 to DEFENSE of the queried creature.
      - No effect on ATTACK.
    """

    def __init__(self, game: Game, attack: int = 1, defense: int = 1) -> None:
        super().__init__(game, attack, defense)

    @property
    def attack(self) -> int:
        """
        Computes effective attack by broadcasting a Query to all creatures.

        :return: Final attack after chain processing.
        """
        q = Query(WhatToQuery.ATTACK, self.initial_attack)
        for c in self.game.creatures:
            c.query(self, q)
        return q.value

    @property
    def defense(self) -> int:
        """
        Computes effective defense by broadcasting a Query to all creatures.

        :return: Final defense after chain processing.
        """
        q = Query(WhatToQuery.DEFENSE, self.initial_defense)
        for c in self.game.creatures:
            c.query(self, q)
        return q.value

    def query(self, source: Creature, query: Query) -> None:
        """
        Adds +1 DEFENSE to *others* in the same Game.

        :param source: The creature whose attribute is being queried.
        :param query: Query message (kind + current value).
        """
        if self is not source and query.what_to_query == WhatToQuery.DEFENSE:
            query.value += 1


class GoblinKing(Goblin):
    """
    Goblin King.

    Rules (in addition to normal Goblin rules):
      - Each Goblin King adds +1 ATTACK to *others* in the same Game.
      - Still contributes +1 DEFENSE as a Goblin.
      - Base stats are (3, 3).
    """

    def __init__(self, game: Game) -> None:
        super().__init__(game, attack=3, defense=3)

    def query(self, source: Creature, query: Query) -> None:
        """
        Adds +1 ATTACK to *others*; otherwise apply Goblin's DEFENSE rule.

        :param source: The creature whose attribute is being queried.
        :param query: Query message (kind + current value).
        """
        if self is not source and query.what_to_query == WhatToQuery.ATTACK:
            query.value += 1
        else:
            super().query(source, query)
