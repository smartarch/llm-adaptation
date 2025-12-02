from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step 1: Move all Warriors to cave; keep a safe core of Farmers in village
        farmers_in_village = []
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "cave")
            else:
                farmers_in_village.append(comp)
                self.environment.assign_group(comp, "farm")

        # Step 2: Ensure a minimal farming backbone in the village
        MIN_VILLAGE_FARMERS = 3
        if len(farmers_in_village) < MIN_VILLAGE_FARMERS:
            # Not enough farmers to spawn safely this turn; skip spawning
            return

        # Step 3: Spawning planning based on current wheat
        total_wheat = int(getattr(environment.farm, "wheat", 0))

        # Farmers available for spawning (beyond the minimal village backbone)
        available_for_spawning = farmers_in_village

        # Reserve at least MIN_VILLAGE_FARMERS to stay in village
        if len(available_for_spawning) <= MIN_VILLAGE_FARMERS:
            return
        spawning_pool = available_for_spawning[MIN_VILLAGE_FARMERS:]

        # Spawn Farmers first: needs 2 farmers and 10 wheat per spawn
        max_spawn_farmer = min(len(spawning_pool) // 2, total_wheat // 10)
        spawn_farmer_count = 2 * max_spawn_farmer

        for i in range(spawn_farmer_count):
            comp = spawning_pool[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Wheat remaining after spawning farmers
        wheat_after_farmer_spawns = total_wheat - (10 * max_spawn_farmer)

        # Remaining farmers after allocating to spawn farmers
        remaining_after_farmer_spawns = spawning_pool[spawn_farmer_count:]

        # Spawn Warriors with remaining farmers and wheat
        max_spawn_warrior = min(len(remaining_after_farmer_spawns) // 2,
                                wheat_after_farmer_spawns // 12)
        spawn_warrior_count = 2 * max_spawn_warrior

        for i in range(spawn_warrior_count):
            comp = remaining_after_farmer_spawns[i]
            self.environment.assign_group(comp, "spawn warrior")

        # Leftover farmers stay in their current groups (farm)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                # Warriors attack the Dragon
                self.environment.assign_group(comp, "attack")
            else:
                # Farmers return to the Village to continue farming/spawning
                self.environment.assign_group(comp, "village")