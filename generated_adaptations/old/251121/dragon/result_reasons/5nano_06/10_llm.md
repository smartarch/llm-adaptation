Reasoning and updated strategy:

- Goal alignment
  - Ensure early Dragon engagement by guaranteeing some Warriors reach the Cave and attack as soon as possible (within the first few steps).
  - Keep all Farmers in the Village for wheat production, but seed spawns conservatively to grow the population without starving the Wheat economy.
  - Spawn only when there are enough potential spawners (two in the spawn group) and enough wheat.
  - All Warriors should end up in the Cave to attack; Farmers stay in the Village (except for the temporary spawn allocations).

- Key improvements over previous attempts
  - Spawn decisions are more conservative and deterministic:
    - Spawn a Farmer only if there are at least 2 Farmers and wheat >= 10.
    - Spawn a Warrior only if there are at least 4 non-spawn Warriors and wheat >= 12.
  - Always route Warriors to the Cave (and only then to Attack in the Cave phase); this ensures early DPS.
  - In the Cave phase, all Warriors attack and Farmers return to Village.

- Expected impact
  - Early DPS from Warriors in Cave accelerates dragon HP reduction.
  - Controlled spawning grows the population gradually, preserving short-term DPS.
  - The strategy adheres to constraints (all Warriors go Cave, all Farmers stay Village, spawn constraints).

Code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Villagers in Village: decide who farms, who goes to Cave, and who spawns
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Read current wheat (robust to missing data)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # 1) Spawn farmer: need at least 2 farmers and wheat >= 10
        spawn_farmer = []
        if len(farmers) >= 2 and wheat >= 10:
            spawn_farmer = farmers[:2]
            for c in spawn_farmer:
                environment.assign_group(c, "spawn farmer")

        # Remaining farmers go to farming
        for c in farmers:
            if c in spawn_farmer:
                continue
            environment.assign_group(c, "farm")

        # 2) Spawn warrior: require at least 4 warriors (including those not used for farmer spawn)
        remaining_warriors = [w for w in warriors if w not in spawn_farmer]
        spawn_warrior = []
        if len(remaining_warriors) >= 4 and wheat >= 12:
            spawn_warrior = remaining_warriors[:2]
            for c in spawn_warrior:
                environment.assign_group(c, "spawn warrior")

        # Remaining warriors (not spawning) should head to the Cave
        for c in remaining_warriors:
            if c not in spawn_warrior:
                environment.assign_group(c, "cave")

        # Farmers that were not assigned to spawn (or farm) are already handled above.
        # If there are any edge cases, they will be re-evaluated in subsequent steps.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```