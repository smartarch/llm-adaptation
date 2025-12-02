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

        assigned_ids = set()

        # Step 1: All Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, 'cave')
            assigned_ids.add(id(c))

        # Step 2: Partition Farmers into non-overlapping final groups using wheat
        local_wheat = 0
        farm_obj = getattr(environment, 'farm', None)
        if farm_obj is not None:
            local_wheat = getattr(farm_obj, 'wheat', 0)

        spawn_farm_count = 0
        if len(farmers) >= 2 and local_wheat >= 10:
            spawn_farm_count = min(len(farmers) // 2, local_wheat // 10)

        # Build sets deterministically
        spawn_farm_set = set()
        idx = 0
        for _ in range(spawn_farm_count):
            a = farmers[idx]
            b = farmers[idx + 1]
            spawn_farm_set.add(a)
            spawn_farm_set.add(b)
            assigned_ids.add(id(a))
            assigned_ids.add(id(b))
            idx += 2

        wheat_left = local_wheat - (spawn_farm_count * 10)

        remaining = [f for f in farmers if f not in spawn_farm_set]
        spawn_warrior_count = 0
        if len(remaining) >= 2 and wheat_left >= 12:
            spawn_warrior_count = min(len(remaining) // 2, wheat_left // 12)

        spawn_warrior_set = set()
        for j in range(spawn_warrior_count):
            a = remaining[2 * j]
            b = remaining[2 * j + 1]
            spawn_warrior_set.add(a)
            spawn_warrior_set.add(b)
            assigned_ids.add(id(a))
            assigned_ids.add(id(b))

        farm_set = [f for f in farmers if f not in spawn_farm_set and f not in spawn_warrior_set]
        for f in farm_set:
            assigned_ids.add(id(f))

        # Step 3: Apply final non-overlapping assignments
        for c in spawn_farm_set:
            environment.assign_group(c, 'spawn farmer')
        for c in spawn_warrior_set:
            environment.assign_group(c, 'spawn warrior')
        for c in farm_set:
            environment.assign_group(c, 'farm')

        # Safety net: assign any unassigned villagers to farm
        for c in components:
            if id(c) not in assigned_ids:
                environment.assign_group(c, 'farm')

        # Optional: adjust wheat to reflect consumption
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