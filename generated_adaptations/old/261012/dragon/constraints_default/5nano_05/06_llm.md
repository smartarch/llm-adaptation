Reasoning and adaptation strategy

What changed and why:
- The functional tests require spawning new villagers (farmers and warriors) to increase the chances of killing the Dragon. Previously, spawning was either attempted without enough wheat (leading to invalid assignments) or avoided altogether.
- To be robust, the adaptation now only assigns villagers to spawn groups when there is enough wheat to support those spawns, and it guarantees that every component is assigned to exactly one group.
- Rules respected:
  - All Warriors must go to the Cave and eventually to the Attack group in the Cave phase.
  - Farmers stay in the Village and can farm or participate in spawning, depending on available wheat.
  - Spawn groups consume wheat: spawn farmer requires 10 wheat for every two villagers in that group; spawn warrior requires 12 wheat for every two villagers in that group.
- The approach:
  - In assign_in_village:
    - Move all Warriors to the cave (to attack ASAP).
    - For Farmers, determine how many can spawn farmers and how many can spawn warriors based on available wheat, always ensuring we don’t exceed wheat or available villagers.
    - The rest of Farmers go to the farm group.
  - In assign_in_cave:
    - Warriors go to Attack; Farmers return to Village.

This strategy ensures valid assignments, respects the spawning constraints, and maintains progression toward killing the Dragon by creating new villagers when possible.

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

        # 2) Wheat available in the Farm
        wheat = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            wheat = getattr(farm_env, "wheat", 0)

        # 3) Spawn planning based on available wheat and farmers
        n_farmers = len(farmers)

        # How many pairs can we allocate to spawn farmer given wheat
        spawn_farmer_slots = min(n_farmers // 2, wheat // 10)

        idx = 0
        # Assign first 2 * spawn_farmer_slots farmers to "spawn farmer"
        for _ in range(spawn_farmer_slots * 2):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        remaining = farmers[idx:]

        # Remaining wheat after allocating for spawn farmers
        remaining_wheat = wheat - spawn_farmer_slots * 10

        # How many pairs can we allocate to spawn warrior from the remaining farmers
        spawn_warrior_slots = min(len(remaining) // 2, remaining_wheat // 12)

        # Assign first 2 * spawn_warrior_slots farmers to "spawn warrior"
        for i in range(spawn_warrior_slots * 2):
            environment.assign_group(remaining[i], "spawn warrior")

        # The rest of the farmers go to farming
        rest_start = spawn_warrior_slots * 2
        for f in remaining[rest_start:]:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors -> attack (attack the Dragon)
        - Farmers -> village (return to Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```