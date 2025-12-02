Reasoning and adaptation strategy:
- Objective: Kill the Dragon as fast as possible using villagers. Warriors should attack from the Cave while Farmers stay in the Village to Farm and to spawn new villagers if wheat allows. We need to continuously grow the population to increase total damage output while ensuring the Dragon is actively attacked.
- Key points:
  - All Warriors should go to the Cave to attack the Dragon.
  - All Farmers should stay in the Village and either farm to produce wheat or participate in spawning to increase population.
  - Spawning rules: For every two villagers assigned to a spawn group and a Wheat threshold (10 for Farmers, 12 for Warriors), a new villager of the respective type is spawned. We should allocate farmers to spawn groups only when we have enough wheat.
  - In the Cave, Warriors should attack the Dragon, Farmers should move to the Village.
- Strategy in steps:
  - assign_in_village:
    - Move all Warriors to the Cave (group "cave").
    - For Farmers, compute how many spawns can be supported given available wheat:
      - Calculate max possible farmer-spawns: min(farmers // 2, wheat // 10)
      - Allocate up to 2 farmer-spawns (to seed growth) if possible. For these spawns, use 2*s_farm farmers assigned to "spawn farmer".
      - After reserving farmers for farmer-spawns, compute possible warrior-spawns with remaining farmers and wheat: min(remaining_farmers // 2, remaining_wheat // 12). Reserve up to 2 war-spawns, and assign 2*s_war farmers to "spawn warrior".
      - Remaining farmers are assigned to "farm" to continue producing wheat.
  - assign_in_cave:
    - Warriors go to "attack" (to fight the Dragon).
    - Farmers go to "village" (to farm or spawn).
- This strategy adheres to the requirement that each component is assigned to exactly one group per step, with explicit re-assignment if the component’s role dictates a change of behavior (e.g., Warriors moving to Cave and attacking, Farmers remaining in Village).

Python code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Move all warriors to cave to go attack later
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available for spawning decisions
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Determine possible spawns given current counts
        max_farm_spawns = 0
        if len(farmers) >= 2 and wheat >= 10:
            max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Limit spawns per step to keep growth steady
        s_farm = min(max_farm_spawns, 2)

        wheat_after_farm = wheat - s_farm * 10
        remaining_farmers = len(farmers) - (2 * s_farm)

        max_war_spawns = 0
        if remaining_farmers >= 2 and wheat_after_farm >= 12:
            max_war_spawns = min(remaining_farmers // 2, wheat_after_farm // 12)

        s_war = min(max_war_spawns, 2)

        spawn_farmer_count = 2 * s_farm
        spawn_warrior_count = 2 * s_war

        # Assign farmers to appropriate groups
        # First spawn farmer group, then spawn warrior group, then remaining to farm
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Note: Warriors were already moved to "cave" above. If there are no Warriors in the village,
        # they won't appear here, which is fine.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack and Farmers to the village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```