Reasoning and adaptation strategy

Goal recap:
- Kill the Dragon as fast as possible.
- All Warriors should go to the Cave to attack the Dragon.
- All Farmers stay in the Village to farm or spawn new villagers.
- Spawning rules: 
  - spawn farmer: for every 2 villagers in the "spawn farmer" group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every 2 villagers in the "spawn warrior" group and 12 wheat, a new Warrior is spawned.
- Wheat production:
  - Farmers farming produce 5 wheat each step.
  - Warriors farming produce 2 wheat each step.
- Dragon behavior: it can deal damage to villagers in the Cave, or eat one.

Strategy overview:
- In the village phase:
  - Move all Warriors to the Cave (prepare to attack).
  - Keep Farmers in the Village to farm or spawn new villagers.
  - Use a simple, adaptive allocation of Farmers to:
    - farm (to steadily increase wheat),
    - spawn farmer (to create more Farmers),
    - spawn warrior (to create more Warriors) when wheat is available.
  - The allocation is constrained by current wheat and the number of Farmers:
    - Always keep at least one Farmer in the farm role to generate wheat if possible.
    - When wheat is abundant and there are enough Farmers, spawn new Farmers and Warriors to accelerate the force needed to overwhelm the Dragon.
- In the cave phase:
  - All Farmers should go back to the Village (they should farm/spawn, not fight).
  - All Warriors (that arrived in the cave) should Attack the Dragon.

This approach ensures immediate deployment of combatants (Warriors) to the Dragon, while Farmers stay to grow wheat and spawn more villagers to sustain or increase offensive capability. The strategy re-evaluates wheat and farmer counts each step, providing a simple but adaptive plan without requiring complex state tracking beyond current wheat and role counts.

Now, the Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # 1) All Warriors should go to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village and farm or spawn new villagers
        #    We keep a simple adaptive distribution among farming, spawn farmer, spawn warrior.

        wheat = getattr(environment.farm, "wheat", 0)

        # If there are no farmers, nothing to allocate
        if not farmers:
            return

        # Heuristic allocation
        assign_farm = []
        assign_spawn_farmer = []
        assign_spawn_warrior = []

        nf = len(farmers)

        # Strategy Rules (simple greedy policy)
        # - If we have at least 4 farmers and high wheat, spawn both farmer and warrior (2 each)
        if nf >= 4 and wheat >= 22:
            assign_spawn_farmer = farmers[:2]
            assign_spawn_warrior = farmers[2:4]
            assign_farm = farmers[4:]
        # - If we have at least 3 farmers and some wheat, spawn a warrior (needs 2 villagers)
        elif nf >= 3 and wheat >= 12:
            assign_spawn_warrior = farmers[:2]
            assign_farm = farmers[2:]
        # - If we have at least 2 farmers and some wheat, spawn a farmer
        elif nf >= 2 and wheat >= 10:
            assign_spawn_farmer = farmers[:2]
            assign_farm = farmers[2:]
        # - Otherwise, just farm with all farmers
        else:
            assign_farm = farmers

        # Apply assignments
        for f in assign_farm:
            environment.assign_group(f, "farm")
        for f in assign_spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in assign_spawn_warrior:
            environment.assign_group(f, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack, Farmers back to Village
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```