

# The Bug: Wrong Group Name

After 7 attempts, I believe the core issue is **the spawn group name**. The prompt explicitly lists the village groups as: **`farm`**, **`cave`**, **`spawn`**. I was calling `"spawn warrior"` and `"spawn farmer"` — names that don't exist in the simulator. Every spawn assignment silently failed, meaning **no new warriors were ever produced**. The starting 2 warriors couldn't kill a 50 HP dragon against counterattacks, so every game was lost.

The engine itself decides whether to produce a Farmer (10 wheat) or a Warrior (12 wheat) from a spawn pair. I cannot control which — I just assign pairs to `"spawn"`.

## Strategy (simple, hard-coded group names from the prompt)

- **Village:** Warriors → `"cave"`. Farmers: pair into `"spawn"`; odd leftover → `"farm"`.
- **Cave:** Warriors → `"attack"` (every turn, unconditional). Non-warriors → `"village"`.
- No wheat checks, no HP checks, no clever logic. Every unit assigned every turn.

```python
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        for c in components:
            role = str(getattr(c, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(c, "cave")
            else:
                # Farmers: try to pair for spawn, else farm.
                # (Pairing logic handled after the loop.)
                pass

        farmers = [c for c in components
                   if str(getattr(c, "role", "")).lower() == "farmer"]

        # Greedy pairing: every two farmers → "spawn"; leftover → "farm"
        num_pairs = len(farmers) // 2
        for i in range(num_pairs * 2):
            environment.assign_group(farmers[i], "spawn")
        for i in range(num_pairs * 2, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            role = str(getattr(c, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```