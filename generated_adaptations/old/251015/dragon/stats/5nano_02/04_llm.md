Reasoning and improved adaptation strategy:

- What went wrong previously
  - The earlier strategy spawned farmers in a somewhat arbitrary way and risked depleting wheat or leaving too many farmers idle. It also didn’t systematically scale spawning with available resources, which limited growth and DPS.
  - Warriors were always sent to the cave and then attack, but spawning logic did not efficiently leverage wheat to grow the villager population.

- Strategy improvements
  - Enforce the constraint that all Warriors go to the cave and then attack, ensuring a steady DPS against the Dragon.
  - Use a resource-aware spawn plan for Farmers to grow the population and wheat production over time:
    - In the village, concentrate on farming and controlled spawning. Use a two-phase spawn decision based on current wheat and the number of Farmers available.
    - Phase 1: Spawn new Farmers as soon as there are at least 2 Farmers available and at least 10 wheat. This creates a reinforcing loop: more Farmers produce more wheat, enabling further spawns.
    - Phase 2: If there are enough Farmers left and wheat is available, spawn new Warriors by placing 2 Farmers in the “spawn warrior” group, consuming 12 wheat per spawn. This increases DPS while keeping Farmers in the village for wheat production.
  - Distribute Farmers into three spawn-related groups and a farming group:
    - spawn farmer: to produce more Farmers
    - spawn warrior: to produce Warriors
    - farm: to continue wheat production
  - In the cave, keep Warriors in attack mode to maximize Dragon damage, while moving Farmers back to the village to farm.

- Expected outcomes
  - More reliable wheat growth, enabling continuous spawning of new villagers.
  - Gradual increase in warrior count, boosting DPS to kill the Dragon within fewer turns.
  - Reduced risk of mass death by limiting the number of villagers in the cave to only Warriors (and their attacks).

Python code (single code block):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Ensure all Warriors move to the Cave to attack (as required)
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")

        # Gather all Farmers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]

        # Wheat available for spawning decisions
        wheat = int(environment.farm.wheat)

        # Number of possible new Farmers we can spawn now:
        # For each new Farmer spawned, we need 2 existing villagers in the spawn group and 10 wheat.
        # We approximate by using the number of Farmers we have as potential spawn participants.
        possible_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Total number of Farmers to assign to the "spawn farmer" group
        spawn_farmers_to_assign = 2 * possible_farm_spawns

        # Update wheat after allocating for farming spawns
        wheat_left_after_farm_spawns = wheat - (10 * possible_farm_spawns)

        # Remaining farmers after allocating to spawn farmer group
        remaining_farmers_after_farm_spawns = farmers[spawn_farmers_to_assign:]

        # Possible Warrior spawns using remaining farmers and remaining wheat
        possible_war_spawns = min(len(remaining_farmers_after_farm_spawns) // 2,
                                  wheat_left_after_farm_spawns // 12)

        spawn_warriors_to_assign = 2 * possible_war_spawns

        # Assign farmers to groups
        for i, f in enumerate(farmers):
            if i < spawn_farmers_to_assign:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmers_to_assign + spawn_warriors_to_assign:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, keep Warriors in the "attack" group; Farmers go to the Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```