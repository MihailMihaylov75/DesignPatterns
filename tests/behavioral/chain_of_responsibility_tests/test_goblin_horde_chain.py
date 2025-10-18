import pytest
from behavioral.chain_of_responsibility.goblin_horde_chain import Game, Goblin, GoblinKing


@pytest.mark.unit
def test_goblin_horde_effects():
    g = Game()
    g1 = Goblin(g); g.creatures.append(g1)
    assert g1.attack == 1 and g1.defense == 1
    g2 = Goblin(g); g.creatures.append(g2)
    assert g1.attack == 1 and g1.defense == 2
    king = GoblinKing(g); g.creatures.append(king)
    assert g1.attack == 2 and g1.defense == 3
