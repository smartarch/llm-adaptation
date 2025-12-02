Reasoning and strategy

Goal recap:
- Keep all Warriors in the Cave to attack the Dragon; Farmers stay in the Village.
- Attack should happen as early as possible (at least once in the first 15 steps).
- Spawn new Farmers and Warriors to boost DPS and wheat production, but only using the valid spawning rules (two villagers in a spawn group + enough wheat).
- Spawn aggressively enough early to increase the chance of killing the Dragon, but avoid starving wheat or delaying the first attack.

What I changed:
- I implemented a more systematic, wheat-aware spawning plan:
  - Move all existing Warriors to the Cave first (attack comes from Cave).
  - In the Village, compute how many Warriors we can spawn early given the current wheat and number of Farmers. We do this in a step-bounded way (step <= 15) to satisfy the early attack requirement.
  - Spawn Warriors first (few pairs of Farmers to "spawn warrior" as allowed by 12 wheat per pair of Farmers).
  - Then spawn Farmers (pairs of Farmers to "spawn farmer" as allowed by the remaining wheat; 10 wheat per pair).
  - Any remaining Farmers stay in the Village and continue farming.
- In assign_in_cave, keep Warriors in attack mode and move Farmers back to the Village, preserving the constraint that Farmers stay in the Village.

This approach aims to guarantee:
- An early attack by ensuring Warriors are moved to the Cave quickly.
- Some early spawns to boost DPS (both new Warriors and Farmers) without starving wheat.
- A balanced growth: enough Warriors in cave to pressure the Dragon, while Farmers keep farming to fuel future spawns.

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

        # 2) Spawn logic (aggressive but gated by wheat and population)
        # Get current wheat in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        idx = 0  # index into farmers list for assigning to spawn groups

        # Early aggressive spawning (step <= 15)
        # First, spawn Warriors if possible: for every 2 farmers, need 12 wheat
        max_possible_war_spawns = 0
        if step <= 15:
            max_possible_war_spawns = min(len(farmers) // 2, wheat // 12)

        # Spawn max_possible_war_spawns * 2 farmers into "spawn warrior" (each pair yields 1 Warrior)
        for _ in range(max_possible_war_spawns):
            if idx + 1 < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                environment.assign_group(farmers[idx + 1], "spawn warrior")
                idx += 2
            else:
                break

        # Recompute remaining wheat after war spawns
        remaining_wheat = wheat - 12 * max_possible_war_spawns

        # Then spawn Farmers if possible: each pair requires 10 wheat
        max_possible_farmer_spawns = 0
        if step <= 15:
            max_possible_farmer_spawns = min((len(farmers) - idx) // 2, remaining_wheat // 10)

        for _ in range(max_possible_farmer_spawns):
            if idx + 1 < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                environment.assign_group(farmers[idx + 1], "spawn farmer")
                idx += 2
                remaining_wheat -= 20

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