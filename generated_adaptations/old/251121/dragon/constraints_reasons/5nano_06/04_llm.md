Reasoning and updated adaptation strategy

Problem understanding:
- The previous implementation occasionally left some Farmers unassigned in assign_in_village, causing test failures. This happened because the logic could end up not assigning a Farmer to any final group when spawn opportunities were not taken.
- The tests require every component to be assigned to exactly one group in assign_in_village, and all Warriors must end up in the Cave, while Farmers stay in the Village (with possible spawning groups).
- To fix this, we switch to an explicit, non-overlapping assignment approach:
  - Always assign all Warriors to the cave.
  - Initially plan Farmer final groups with a default of Farm, but override this with spawn groups in a non-overlapping manner:
    - Determine spawn_farm_candidates (2 or 4 Farmers) based on the Wheat in the Farm.
    - From the remaining Farmers, determine spawn_warrior_candidates (2 Farmers) if Wheat allows.
    - The rest of the Farmers will stay in Farm.
  - This guarantees every Farmer is assigned to exactly one of: spawn farmer, spawn warrior, or farm.
- In assign_in_cave, keep the rule that Warriors go to Attack and Farmers return to Village (village group).

Strategy specifics:
- In assign_in_village:
  - Move all Warriors to the cave (attack later in cave step).
  - Assign Farmers as follows (non-overlapping):
    - If possible, pick 4 Farmers for spawn farmer (requires at least 20 wheat).
    - Else if possible, pick 2 Farmers for spawn farmer (requires at least 10 wheat).
    - From the remaining Farmers, if possible, pick 2 for spawn warrior (requires at least 12 wheat).
    - The rest of Farmers go to Farm.
- In assign_in_cave:
  - Warriors go to Attack to fight Dragon.
  - Farmers go back to Village.

This guarantees:
- All farmers are assigned exactly once.
- All warriors are in the cave and attack.
- Spawning opportunities are utilized when resources allow, while not overlapping assignments.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into groups:
        - 'farm': stay in village and farm
        - 'cave': go to the cave (we'll move Warriors here; in cave step they attack)
        - 'spawn farmer': use 2 villagers + 10 wheat to spawn a new Farmer
        - 'spawn warrior': use 2 villagers + 12 wheat to spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, 'cave')

        # Step 2: Default: all Farmers go to Farm
        for c in farmers:
            environment.assign_group(c, 'farm')

        # Step 3: Determine spawn opportunities based on current Wheat
        local_wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        # Prepare non-overlapping spawn groups
        spawn_farm_candidates = []
        if len(farmers) >= 4 and local_wheat >= 20:
            spawn_farm_candidates = farmers[:4]
        elif len(farmers) >= 2 and local_wheat >= 10:
            spawn_farm_candidates = farmers[:2]

        remaining_after_farm = [f for f in farmers if f not in spawn_farm_candidates]

        spawn_warrior_candidates = []
        if len(remaining_after_farm) >= 2 and local_wheat >= 12:
            spawn_warrior_candidates = remaining_after_farm[:2]

        rest_to_farm = [f for f in farmers if f not in spawn_farm_candidates and f not in spawn_warrior_candidates]

        # Step 4: Apply final non-overlapping assignments
        for c in spawn_farm_candidates:
            environment.assign_group(c, 'spawn farmer')
        for c in spawn_warrior_candidates:
            environment.assign_group(c, 'spawn warrior')
        for c in rest_to_farm:
            environment.assign_group(c, 'farm')

        # Note: Warriors were already moved to 'cave'. Farmers defaulted to 'farm' or overridden by spawn groups.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into groups:
        - 'attack': Attack the Dragon
        - 'cave': Stay in the Cave
        - 'village': Go to the Village
        """
        for c in components:
            role = getattr(c, 'role', None)
            if role == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers (and any other non-warrior) go back to Village
                environment.assign_group(c, 'village')
```