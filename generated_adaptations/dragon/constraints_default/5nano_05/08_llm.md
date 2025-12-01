Reasoning and adaptation strategy

Issue analysis:
- Tests require spawning new farmers and new warriors to increase the chance of killing the Dragon. The previous approach could starve wheat production by moving too many farmers into spawn groups, or fail to spawn warriors early enough, especially when starting with no initial warriors.
- A robust strategy must:
  - Guarantee every component is assigned exactly once.
  - Respect spawning constraints (two villagers in a spawn group plus required wheat).
  - Maintain some wheat production by leaving at least one farmer in the farm role whenever possible.
  - Spawn farmers and warriors gradually as wheat becomes available, to increase the chance of victory across the game.

Updated strategy:
- In assign_in_village:
  - Move all Warriors to the cave (to attack the Dragon as soon as possible).
  - For Farmers, allocate spawning only up to a limit that leaves at least one Farmer to continue farming (to keep wheat production going).
  - Compute how many Farmer-spawn pairs can be created given available wheat (needs 10 wheat per 2 Farmers).
  - After allocating Farmer spawns, compute how many Warrior-spawn pairs can be created from the remaining Farmers given remaining wheat (needs 12 wheat per 2 Warriors).
  - Any Farmers not allocated to spawn groups go to the "farm" group.
- In assign_in_cave:
  - Warriors go to "attack" (to attack the Dragon).
  - Farmers go to "village" (return to the Village to farm/spawn).

This approach ensures valid assignments, respects wheat constraints, maintains ongoing farming for wheat production, and provides a gradual path to spawning new Warriors while still enabling early dragon engagement.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Move all Warriors to the Cave (to eventually Attack)
        - For Farmers, spawn new villagers when wheat allows:
          * spawn farmer: for every 2 villagers in the group and 10 wheat, a new Farmer is spawned
          * spawn warrior: for every 2 villagers in the group and 12 wheat, a new Warrior is spawned
        - Remaining Farmers go to the farm group
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # If there are no farmers, nothing to spawn; just return (Warriors already moved)
        if not farmers:
            return

        # 2) Wheat available in the Farm
        wheat = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            wheat = getattr(farm_env, "wheat", 0)

        n_farmers = len(farmers)

        # Ensure at least one farmer stays in farming to keep wheat production
        min_farmers_for_farm = 1 if n_farmers > 0 else 0
        max_spawnable = max(0, n_farmers - min_farmers_for_farm)

        # Number of pairs for spawning farmers
        spawn_farmer_slots = max(0, min(max_spawnable // 2, wheat // 10))

        idx = 0
        # Assign 2 * slots farmers to "spawn farmer"
        for _ in range(spawn_farmer_slots * 2):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        remaining = farmers[idx:]
        remaining_wheat = wheat - spawn_farmer_slots * 10

        # Now attempt to spawn warriors from the remaining farmers
        spawn_warrior_slots = max(0, min(len(remaining) // 2, remaining_wheat // 12))

        for i in range(spawn_warrior_slots * 2):
            environment.assign_group(remaining[i], "spawn warrior")

        rest_start = spawn_warrior_slots * 2
        for f in remaining[rest_start:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors -> attack (attack the Dragon)
        - Farmers  -> village (return to Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```