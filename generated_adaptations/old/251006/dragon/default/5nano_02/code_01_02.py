from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (we move Warriors here to prepare for attack)
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a new Farmer
        - spawn warrior: for every two villagers assigned here and 12 wheat, spawn a new Warrior
        """
        # Separate by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Move all Warriors to the Cave (attack group)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Distribute Farmers among the spawn and farming groups
        n = len(farmers)

        # Determine spawn allocations
        # Ensure we only spawn if we have groups with at least two villagers
        spawn_farmer_count = 2 if n >= 2 else 0
        remaining_after_farmer = n - spawn_farmer_count
        spawn_warrior_count = 2 if remaining_after_farmer >= 2 else max(0, remaining_after_farmer)
        farm_count = remaining_after_farmer - spawn_warrior_count

        idx = 0
        # Assign to spawn farmer (first two if possible)
        for i in range(spawn_farmer_count):
            environment.assign_group(farmers[idx + i], "spawn farmer")
        idx += spawn_farmer_count

        # Assign to spawn warrior (next two if possible)
        for i in range(spawn_warrior_count):
            environment.assign_group(farmers[idx + i], "spawn warrior")
        idx += spawn_warrior_count

        # Remaining farmers go to farming
        for i in range(idx, n):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        Strategy: All Warriors should attack; Farmers should go to the Village.
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")