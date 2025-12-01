Reasoning and improved adaptation strategy

Why the original approach underperformed:
- It aggressively sent all Warriors to the cave immediately, which is good for damage, but it didn’t balance farming and spawns. Without enough wheat, spawns stall, limiting future warrior growth.
- It didn’t explicitly protect a minimum farming base to continuously generate wheat, so the army growth could stall, delaying dragon kill.
- Spawns rely on both enough farmers and wheat; if we starve farming while we try to spawn, wheat production can collapse and the dragon survives longer than 30 steps.

What the improved strategy changes:
- Use a greedy, but balanced, spawn policy in the village that always keeps at least a small farming base (at least 2 farmers kept for farming when possible).
- From the remaining farmers, spawn as many Warriors as possible (to maximize early damage), constrained by available wheat (12 per Warrior spawn pair).
- After allocating Warrior spawns, use any remaining farmers and wheat to spawn Farmers (10 wheat per Farmer spawn pair) to grow wheat production for future steps.
- All Warriors go to the cave to attack; Farmers stay in the village either farming or spawning, to maximize wheat production and future spawns.
- In the cave, simply send Warriors to attack and move Farmers back to the village.

This approach aims to maximize early damage from Warriors while ensuring wheat production grows steadily to support more spawns, leading to faster dragon kill within 30 steps.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Strategy:
        # - Keep at least 2 farmers for farming (if possible)
        # - Spawn as many Warriors as possible with remaining farmers and wheat
        # - Then spawn Farmers with what's left

        # Compute Warrior spawns: each pair uses 2 farmers and 12 wheat
        if F >= 3:
            # Reserve at least 2 farmers for farming, use the rest for Warrior spawns
            max_warrior_pairs_by_farmers = (F - 2) // 2
            max_warrior_pairs_by_wheat = W // 12
            warrior_pairs = min(max_warrior_pairs_by_farmers, max_warrior_pairs_by_wheat)
        else:
            warrior_pairs = 0

        spawn_warrior_count = 2 * warrior_pairs

        # Remaining farmers after Warrior spawns
        remaining_farmers_after_warrior = F - spawn_warrior_count

        # Compute Farmer spawns: each pair uses 2 farmers and 10 wheat
        if remaining_farmers_after_warrior >= 2:
            max_farm_pairs_by_farmers = remaining_farmers_after_warrior // 2
            max_farm_pairs_by_wheat = W // 10
            farm_pairs = min(max_farm_pairs_by_farmers, max_farm_pairs_by_wheat)
        else:
            farm_pairs = 0

        spawn_farm_count = 2 * farm_pairs

        # Assign groups for farmers
        idx = 0
        for f in farmers:
            if idx < spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            elif idx < spawn_warrior_count + spawn_farm_count:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")
            idx += 1

        # All warriors should go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, have Warriors attack; Farmers return to village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: stay in cave for safety
                environment.assign_group(c, "cave")
```