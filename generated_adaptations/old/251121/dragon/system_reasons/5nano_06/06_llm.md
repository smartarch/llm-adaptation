Reasoning and strategy

Goal: improve the speed of killing the Dragon while satisfying all constraints.

Key observations:
- Warriors are the primary DPS and must always end up in the Cave to attack the Dragon.
- Farmers keep farming for wheat to fuel spawning, which can bring in more villagers (Farmers and Warriors) to increase DPS and sustain spawning.
- Early attack is important: we should ensure at least one Warrior reaches the Cave and attacks within the first 15 steps if possible.
- Spawning costs (wheat) and group requirements mean we should be careful not to starve wheat or permanently divert farmers away from farming too aggressively.
- A robust improvement is to:
  - Always move existing Warriors to the Cave first (they’ll attack when in the Cave).
  - Keep a small buffer of Farmers farming to accumulate wheat for spawning.
  - Use small, controlled spawning bursts early (before step 15) to generate at least 1-2 Warriors quickly and add a few Farmers later if wheat allows.
  - After spawning decisions, ensure remaining Farmers stay in the Village to farm.

Proposed changes:
- Aggressive but gated early spawning:
  - If step <= 15 and there are at least 4 Farmers and wheat >= 12, allocate 2 Farmers to spawn Warrior (to generate an early extra Warrior).
  - If there are at least 4 additional Farmers and wheat >= 20, allocate 4 Farmers to spawn Farmer (to potentially add up to 2 new Farmers, increasing future wheat production).
- Always route Warriors to the Cave for attack; Farmers stay in Village (farm or participate in spawning groups).

This approach aims to guarantee an earlier Dragon DPS via Warriors in the Cave, while maintaining wheat flow to enable further spawning, and keeping Farmers in the Village for farming.

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all current Warriors to the Cave (they will attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available in Farm (read-only in this interface)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        idx = 0  # index into farmers list for assigning to spawn groups

        # 2) Early aggressive spawning (biased to get DPS early)
        # If we can, spawn a Warrior early (step <= 15)
        if step <= 15 and len(farmers) - idx >= 4 and wheat >= 12:
            for _ in range(2):  # assign two farmers to spawn warrior
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Spawn farmers if wheat allows (up to 2 new farmers via 4 farmers in group)
        if step <= 15 and len(farmers) - idx >= 4 and wheat >= 20:
            for _ in range(4):  # assign four farmers to spawn farmer
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers stay in the village and farm
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: all Warriors attack; Farmers go to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```