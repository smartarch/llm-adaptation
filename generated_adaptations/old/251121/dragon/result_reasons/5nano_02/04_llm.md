Reasoning and improved strategy

Observations:
- Warriors are the primary damage dealers (3 damage each), but they must be in the Cave to attack.
- Spawning new villagers requires both group assignments and wheat. Spawning consumes wheat and two villagers per spawn group.
- To maximize early damage, we should:
  - Move all current warriors to the Cave so they can start attacking as soon as possible.
  - Keep Farmers in the Village farming early to accumulate wheat quickly, enabling spawn bursts soon after.
  - Use a simple, step-aware spawning policy: as soon as enough wheat and farmers exist, spawn some Warriors (and optionally Farmers) to bolster DPS without starving future wheat production.
  - Ensure the Dragon is attacked within the first 15 steps by keeping Warriors in the attack group in the Cave as soon as they arrive there.

Key approach:
- assign_in_village
  - Move all Warriors to the Cave immediately (to start attacking).
  - For Farmers, use a lightweight, step-aware greedy:
    - If step is early and there is enough wheat, spawn both Warriors and Farmers (e.g., 2 Warriors and 2 Farmers) by designating 4 Farmers to the spawn groups, consuming 22 wheat total.
    - Otherwise, spawn at most one of the two types per step when wheat allows (prefer spawning Warriors when there are enough Farmers, then Farmers), otherwise keep Farmers farming.
  - The rest of the Farmers stay in farming (group "farm").
  - This keeps a balance between growing the army and maintaining wheat income.

- assign_in_cave
  - All Warriors go to "attack".
  - All Farmers go to "village" (to stay or return to village for farming/spawns next turn).

This strategy aims to:
- Ensure early Dragon damage via Warriors in the Cave.
- Grow the force with spawns as soon as resources permit, without starving ongoing wheat production.
- Keep at least half of the active Warriors available in the Cave to attack the Dragon across steps.

Python implementation

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village-side logic:
        - Move all existing Warriors to the cave (to attack early).
        - Use a simple, step-aware spawning heuristic for Farmers to create new Farmers/Warriors.
        - Remaining Farmers stay in farming.
        """

        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all existing Warriors to the Cave (they will attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Decide spawning vs farming for Farmers
        total_farmers = len(farmers)
        spawn_warrior = 0
        spawn_farmer = 0
        farm_count = total_farmers  # default: all farmers farm

        # Wheat available in the farm area (read-only in this environment)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Heuristic: try to spawn early if resources permit
        # Case A: strong resources -> spawn 2 Warriors and 2 Farmers (uses 22 wheat, 4 farmers)
        if step >= 3 and total_farmers >= 4 and wheat >= 22:
            spawn_warrior = 2
            spawn_farmer = 2
            farm_count = total_farmers - 4
        # Case B: moderate resources -> spawn 2 Warriors (uses 12 wheat, 2 farmers)
        elif step >= 3 and total_farmers >= 2 and wheat >= 12:
            spawn_warrior = 2
            farm_count = total_farmers - 2
        # Case C: mild resources -> spawn 1 Warrior (uses 2 farmers, 12 wheat)
        elif step >= 4 and total_farmers >= 2 and wheat >= 12:
            spawn_warrior = 2
            farm_count = total_farmers - 2
        # Case D: only farming possible -> spawn 2 Farmers if possible (requires 10 wheat)
        elif step >= 4 and total_farmers >= 2 and wheat >= 10:
            spawn_farmer = 2
            farm_count = total_farmers - 2
        # Fallback: no spawns this step, all farm
        else:
            farm_count = total_farmers

        # Assign Farmers to their groups in a simple deterministic order
        idx = 0
        # spawn warrior (2 villagers per spawn)
        for _ in range(spawn_warrior):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # spawn farmer (2 villagers per spawn)
        for _ in range(spawn_farmer):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # remaining farmers farm
        for _ in range(farm_count):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], "farm")
                idx += 1

        # Safety: if any farmers are left (due to ordering), farm them
        while idx < total_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave-side logic:
        - All Warriors go to attack the Dragon.
        - All Farmers go back to the Village.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should stay in the Village
                environment.assign_group(c, "village")
```