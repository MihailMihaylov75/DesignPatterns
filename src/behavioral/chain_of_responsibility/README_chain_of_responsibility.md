
# Chain of Responsibility — Design Pattern (Python 3.11+)

This directory contains **four implementations** of the *Chain of Responsibility* (CoR) design pattern, each focusing on a slightly different real-world context.

---

##  1. `method_chain.py`
**Concept:** Sequential handlers linked together (canonical CoR).  
**Use when:** You have a series of independent checks or transformations where each handler may stop or delegate further.

**Example:**
```python
chain = build_default_chain()
req = Request("create_order", {"user_id": "u1", "items": ["A"]})
result = chain.handle(req)
print(result.message)  # "Order validated"
```

**Typical use cases:**
- Request validation pipelines (auth -> rate-limit -> business rules)
- Command or message filtering systems
- Modular UI or API middle layers

---

##  2. `ui_chain.py`
**Concept:** Robust UI interaction sequence as a handler chain.  
**Use when:** Each UI step must pass several preconditions (visibility, stability, etc.) before executing.

**Example:**
```python
flow = build_ui_click_flow()
req = UIRequest(driver, by="css selector", value="#submit-btn")
result = flow.handle(req)
assert result.success, result.message
```

**Typical use cases:**
- Selenium / Playwright test flows
- Reusable "macro" actions with stable preconditions
- Chains of visual or functional verifications

---

##  3. `goblin_horde_chain.py`
**Concept:** Event-driven CoR (Observer flavor).  
**Use when:** Multiple entities must *react* to a query and modify shared data.

**Example:**
```python
game = Game()
g1, g2, king = Goblin(game), Goblin(game), GoblinKing(game)
game.creatures += [g1, g2, king]
print(g1.attack, g1.defense)  # (2, 3)
```

**Typical use cases:**
- Game logic with modifiers/buffs
- Event-broker systems
- Dynamic attribute computation

---

## ️ 4. `broken_chain.py`
**Concept:** Event-bus based CoR with *query mutators*.  
**Use when:** You need an extensible notification model where observers adjust data in flight.

**Example:**
```python
game = Game()
goblin = Creature(game, "Strong Goblin", 2, 2)
with DoubleAttackModifier(game, goblin):
    print(goblin.attack)  # doubled
```

**Typical use cases:**
- Extensible domain rules
- Plugin or modifier systems
- "Reactive" stat calculation

---

##  When to Use Chain of Responsibility

✅ The exact handler that should process a request isn’t known beforehand.  
✅ You want to **avoid massive `if/elif` blocks**.  
✅ You want to **add/remove processing steps dynamically**.  
✅ You prefer **loose coupling** between request senders and receivers.

**Anti-pattern indicators:**

❌ When every handler *must* process the request (use Pipeline instead).  
❌ When execution order is not well-defined or debugging becomes difficult.

---

##  Summary

| File | Pattern Flavor | Key Concept |
|------|----------------|--------------|
| `method_chain.py` | Canonical | Sequential handler delegation |
| `ui_chain.py` | Practical / Testing | UI precondition flow |
| `goblin_horde_chain.py` | Event-based | Creatures reacting to queries |
| `broken_chain.py` | Event-bus / Modifier | Reactive attribute adjustments |

---

**Author:** Mihail Mihaylov  
**Language:** Python 3.11+  
**License:** MIT  
**Tags:** `Behavioral`, `Design Pattern`, `Selenium`, `Event-driven`, `Testing`

---
