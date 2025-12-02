Reasoning and updated adaptation strategy

Problem observed:
- Tests continue to flag assignment errors in assign_in_village, meaning some farmers were not assigned exactly once, or were assigned to multiple groups.
- Functional constraints require spawning new warriors (and farmers) to improve odds against the Dragon. In some test seeds, the previous logic did not spawn enough warriors early enough.

Strategy refinement:
- Guarantee a clean, non-overlapping assignment for farmers in assign_in_village by using a deterministic, single-pass partition:
  - Move all Warriors to the Cave (group "cave").
  - Partition Farmers into three non-overlapping subgroups in a single pass:
    - spawn farmer: uses 2 farmers and 10 wheat per spawn.
    - spawn warrior: uses 2 farmers and 12 wheat per spawn.
    - farm: all remaining farmers.
- To avoid assignment duplication, assign farmers sequentially based on the computed spawn counts, without previously assigning defaults that could overlap.
- Spawn logic prioritizes creating at least one farmer spawn when wheat allows, and also attempts to create at least one warrior spawn whenever possible given remaining wheat and farmers. This ensures the “a few new farmers” and “a few new warriors” constraints are more likely to be satisfied across seeds.
- In assign_in_cave, keep Warriors attacking the Dragon and Farmers returning to the Village.

Key points:
- Each farmer is assigned exactly once in assign_in_village.
- Warriors are assigned to the cave once and will attack in the cave step.
- Spawn decisions are made with simple, resource-aware rules to maximize the chance of meeting functional constraints across seeds.

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
        - 'cave': go to the cave (Warriors will be moved here; will attack in cave step)
        - 'spawn farmer': use 2 villagers + 10 wheat to spawn a new Farmer
        - 'spawn warrior': use 2 villagers + 12 wheat to spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Step 1: All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, 'cave')

        # Step 2: Partition Farmers into non-overlapping final groups using wheat
        local_wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            local_wheat = getattr(farm_obj, 'wheat', 0)

        spawn_farm_count = 0
        spawn_warrior_count = 0

        # Prefer a combined spawn if resources allow: 1 farmer-pair + 1 warrior-pair (needs 22 wheat and 4 farmers)
        if len(farmers) >= 4 and local_wheat >= 22:
            spawn_farm_count = 1  # one pair for spawning a farmer
            wheat_after_farm = local_wheat - 10
            # Check if we can also spawn a warrior with remaining wheat and farmers
            if len(farmers) - 2 >= 2 and wheat_after_farm >= 12:
                spawn_warrior_count = 1
        else:
            # If we can't do both, try to spawn at least one warrior when possible
            if local_wheat >= 12 and len(farmers) >= 2:
                spawn_warrior_count = 1
            # If we can't spawn a warrior, try to spawn a farmer if possible
            if spawn_warrior_count == 0 and local_wheat >= 10 and len(farmers) >= 2:
                spawn_farm_count = 1

        idx = 0
        # assign spawn farmer pairs
        for _ in range(spawn_farm_count):
            environment.assign_group(farmers[idx], 'spawn farmer')
            environment.assign_group(farmers[idx + 1], 'spawn farmer')
            idx += 2

        # assign spawn warrior pairs
        for _ in range(spawn_warrior_count):
            environment.assign_group(farmers[idx], 'spawn warrior')
            environment.assign_group(farmers[idx + 1], 'spawn warrior')
            idx += 2

        # rest go to farming
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], 'farm')

        # Optional: adjust wheat in farm to reflect consumption, if possible
        if farm_obj is not None and hasattr(farm_obj, 'wheat'):
            consumed = spawn_farm_count * 10 + spawn_warrior_count * 12
            try:
                farm_obj.wheat = max(0, local_wheat - consumed)
            except Exception:
                pass

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
                environment.assign_group(c, 'village')
```