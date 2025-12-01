Reasoning and adaptation strategy

Task overview:
- Warriors are best used for direct combat: send all Warriors to the Cave to attack the Dragon.
- Farmers are the engine for growth: keep them in the Village to farm (produce wheat) and to spawn new villagers when enough wheat is available.
- Spawning mechanics: you can create new Farmers or Warriors by placing villagers into the spawn groups in the Village. For each two villagers assigned to a spawn group and the required wheat, one new villager of the corresponding type is spawned. Specifically:
  - spawn farmer: costs 10 wheat and requires at least two villagers in this group to spawn one new Farmer.
  - spawn warrior: costs 12 wheat and requires at least two villagers in this group to spawn one new Warrior.
- All Farmers should remain in the Village to farm or participate in spawning; all Warriors should go to the Cave to attack the Dragon.

Strategy:
- In assign_in_village:
  - Move all Warriors to the cave (they should all attack the Dragon).
  - For Farmers, use a simple, deterministic allocation that always keeps most in farming, while reserving a small number for spawning:
    - If there are at least 2 farmers, assign up to 2 farmers to "spawn farmer" to enable potential Farmer spawns.
    - If there are enough farmers left, assign up to 2 farmers to "spawn warrior" to enable potential Warrior spawns.
    - The remaining Farmers go to "farm" to continue producing wheat.
  - This approach ensures a steady wheat supply for spawns and a growing army of villagers over time, while keeping Warriors focused on dragon combat.

- In assign_in_cave:
  - Move all Warriors to the "attack" group to actively attack the Dragon.
  - Move all Farmers back to the Village (group "village") to continue farming or to participate in spawning.

This strategy aims to maximize Dragon damage with Warriors while maintaining a wheat-producing population in the Village and using spawns to gradually bolster both Farmers and Warriors.

Python code (class SmartAdaptation)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the cave (to attack the Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Allocate farmers to farming/spawn groups
        # We'll reserve up to 2 farmers for "spawn farmer" and up to 2 for "spawn warrior"
        # Rest go to farming.
        s_f_spawn = min(2, len(farmers) // 2)
        remaining_farmers_after_f_spawn = len(farmers) - s_f_spawn
        s_w_spawn = min(2, remaining_farmers_after_f_spawn // 2)
        s_farm = remaining_farmers_after_f_spawn - s_w_spawn

        idx = 0
        # Assign to "spawn farmer"
        for _ in range(s_f_spawn):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Assign to "spawn warrior"
        for _ in range(s_w_spawn):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers -> "farm"
        for _ in range(s_farm):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # If any farmers remain (edge cases), assign them to farming as a fallback
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```