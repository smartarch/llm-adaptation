Reasoning and improved adaptation strategy

Goal refinement
- Preserve the constraint: all Warriors go to the Cave and attack the Dragon; Farmers stay in the Village to farm or spawn new villagers.
- Use spawning to accelerate growth when wheat is available:
  - spawn farmer: for every 2 villagers assigned to this group and 10 wheat, spawn a new Farmer.
  - spawn warrior: for every 2 villagers assigned to this group and 12 wheat, spawn a new Warrior.
- Optimize group assignment to maximize early damage while maintaining wheat production.

Key improvements over the prior strategy
- Dynamic spawning in the village based on current wheat and number of Farmers:
  - We allocate as many “spawn farmer” groups as possible given the number of Farmers and available wheat.
  - We also allocate possible “spawn warrior” groups using remaining Farmers if there is enough wheat (this yields faster reinforcement of Warriors, which can speed up Dragon damage in subsequent steps).
- Deterministic, reproducible grouping: we assign the first 2*k villagers to each spawn group in a predictable order, avoiding randomness.
- All Warriors are still sent to the Cave for attacking; Farmers handle farming and spawning. No Warriors are kept in the village to farm (in line with the constraint).

Assignment logic (high level)
- In assign_in_village:
  - Move all Warriors to the cave immediately (as required).
  - Use only Farmers in the village to spawn:
    - Compute max possible Farmer spawns given current wheat (spf).
    - After allocating 2*spf Farmers to "spawn farmer", compute how many additional 2-villager chunks you can allocate to "spawn warrior" using remaining Farmers and remaining wheat (swpawns).
    - Assign farmers in a deterministic order: first 2*spf to "spawn farmer", next 2*swpawns to "spawn warrior", remainder to "farm".
  - This yields a population boost via spawns when wheat is sufficient and farmers are available, while ensuring farming continues when spawns aren’t feasible.
- In assign_in_cave:
  - Warriors go to "attack" (to assault the Dragon).
  - Farmers go to "village" (to continue farming or spawning there).

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning plan using Farmers only (Warriors are not available in village due to step 1)
        n_farmers = len(farmers)
        wheat = 0
        # Safely access environment.farm.wheat
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Maximum number of "spawn farmer" actions we can support
        spf = min(n_farmers // 2, wheat // 10)
        spf2 = spf * 2  # number of farmers allocated to "spawn farmer"

        remaining_farmers_after_farmer_spawns = n_farmers - spf2
        remaining_wheat_after_farmer_spawns = wheat - spf * 10

        # Maximum number of "spawn warrior" actions we can support with remaining farmers and wheat
        swpawns = min(remaining_farmers_after_farmer_spawns // 2,
                       remaining_wheat_after_farmer_spawns // 12)
        spw2 = swpawns * 2  # number of farmers allocated to "spawn warrior"

        # Allocate farmers in a deterministic order:
        # - first 2*spf to "spawn farmer"
        # - next 2*swpawns to "spawn warrior"
        # - the rest to "farm"
        for idx, f in enumerate(farmers):
            if idx < spf2:
                environment.assign_group(f, "spawn farmer")
            elif idx < spf2 + spw2:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack, Farmers back to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```