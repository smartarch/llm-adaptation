Strategy and reasoning (improved approach)

Goal: Kill the Dragon faster by maximizing early DPS and ensuring both immediate attacks and resource-driven spawns.

Key improvements over the previous approach:
- Greedy, multi-round spawning: In the village phase, we now exhaust wheat to spawn as many new Farmers and Warriors as possible in the same step. We do this by first spawning as many Warriors as possible (needs 2 farmers per Warrior and 12 wheat), then using any remaining wheat to spawn as many Farmers as possible (needs 2 farmers per Farmer and 10 wheat). This maximizes the number of attackers and future farmers in one go.
- All Warriors go to Cave and attack as soon as possible: We move all current Warriors to the Cave in the village phase, and in the cave phase we assign them to the attack group so they begin damaging the Dragon immediately.
- Farmers stay in Village: Farmers are kept in the Village unless used for spawning. Spawn groups ("spawn farmer" and "spawn warrior") reside in the Village context to meet the required spawning rules.
- Constraints respected: Every component is assigned to exactly one group. If a component’s role must continue in the same action, we explicitly reassign it to the required group (e.g., Warriors to cave, then to attack in cave).
- Early Dragon damage: By funneling warriors to the cave immediately, we ensure the Dragon is attacked early (within the first few steps, constrained by turn order). The additional spawns increase long-term DPS without violating the rules.

What changed:
- assign_in_village now exhausts wheat via a loop-like approach (greedy spawning) to maximize both Warrior and Farmer spawns in one step.
- assign_in_cave remains straightforward but ensures Warriors go to attack and Farmers go to village.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all current Warriors to the Cave (they will be attacking once in cave)
        for w in warriors:
            if "cave" in group_ids:
                environment.assign_group(w, "cave")

        # 2) Greedily spawn new Villagers using wheat
        # Use a local wheat counter to maximize spawns in this step
        wheat = getattr(environment.farm, "wheat", 0)

        # List of farmers still in village (unassigned)
        unassigned = list(farmers)

        # First, spawn as many Warriors as possible:
        # Each Warrior spawn consumes 2 farmers + 12 wheat
        idx = 0
        max_warriors = min(len(unassigned) // 2, wheat // 12) if len(unassigned) >= 2 else 0
        for _ in range(max_warriors * 2):
            if idx < len(unassigned) and "spawn warrior" in group_ids:
                environment.assign_group(unassigned[idx], "spawn warrior")
            idx += 1
        wheat -= max_warriors * 12

        # Then, spawn as many Farmers as possible with remaining wheat:
        remaining_farmers = unassigned[idx:]
        max_farmers = min(len(remaining_farmers) // 2, wheat // 10) if len(remaining_farmers) >= 2 else 0
        for _ in range(max_farmers * 2):
            fid = idx
            if fid < len(unassigned) and "spawn farmer" in group_ids:
                environment.assign_group(unassigned[fid], "spawn farmer")
            idx += 1
        wheat -= max_farmers * 10

        # 3) Remaining farmers (if any) go to farming in the Village
        for j in range(idx, len(unassigned)):
            if "farm" in group_ids:
                environment.assign_group(unassigned[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors attack Dragon, Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                if "attack" in group_ids:
                    environment.assign_group(c, "attack")
                elif "cave" in group_ids:
                    environment.assign_group(c, "cave")
            else:
                if "village" in group_ids:
                    environment.assign_group(c, "village")
```