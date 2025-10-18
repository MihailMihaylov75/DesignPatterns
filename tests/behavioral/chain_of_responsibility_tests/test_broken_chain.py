import pytest
from behavioral.chain_of_responsibility.broken_chain import Game, Creature, DoubleAttackModifier,\
    IncreaseDefenseModifier


class StrongCreature(Creature):
    def __init__(self, game):
        super().__init__(game, name="Strong Goblin", attack=2, defense=2)


@pytest.mark.unit
def test_modifiers_double_attack_and_increase_defense():
    game = Game()
    gob = StrongCreature(game)
    assert gob.attack == 2 and gob.defense == 2
    with DoubleAttackModifier(game, gob):
        assert gob.attack == 4
        with IncreaseDefenseModifier(game, gob):
            assert gob.defense == 5
    assert gob.attack == 2 and gob.defense == 2
