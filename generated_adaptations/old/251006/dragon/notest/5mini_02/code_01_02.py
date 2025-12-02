from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - In the Village:
      * All warriors are sent to the Cave.
      * Farmers are split into: spawn warrior pairs (if wheat and enough farmers),
        then spawn farmer pairs (if wheat remains and enough farmers), and the rest farm.
      * Always keep at least one farmer farming when possible.
    - In the Cave:
      * All warriors are assigned to "attack".
      * Any farmers in the cave are sent back to the "village".
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group names expected:
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Partition components by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # 1) Send all warriors in the Village to the Cave
        for w in warriors:
            environment.assign_group(w, CAVE)

        # 2) Decide spawn allocation among farmers
        n_farmers = len(farmers)
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Keep at least one farmer farming if any farmers exist (so we still produce wheat)
        min_farmers_kept = 1 if n_farmers > 0 else 0

        available_for_spawn = max(0, n_farmers - min_farmers_kept)

        # Prioritize spawning warriors (cost 12 wheat per spawn, requires 2 villagers per spawn)
        max_warrior_spawns_by_wheat = wheat // 12
        max_warrior_spawns_by_people = available_for_spawn // 2
        warrior_spawns_to_do = min(max_warrior_spawns_by_wheat, max_warrior_spawns_by_people)

        # Reserve villagers for warrior spawns
        villagers_for_warrior_spawn = warrior_spawns_to_do * 2
        wheat_after_warrior_spawns = wheat - (warrior_spawns_to_do * 12)
        available_for_spawn -= villagers_for_warrior_spawn

        # Next, try to spawn farmers (cost 10 wheat per spawn)
        max_farmer_spawns_by_wheat = wheat_after_warrior_spawns // 10
        max_farmer_spawns_by_people = available_for_spawn // 2
        farmer_spawns_to_do = min(max_farmer_spawns_by_wheat, max_farmer_spawns_by_people)

        villagers_for_farmer_spawn = farmer_spawns_to_do * 2
        # remaining farmers will farm
        # Assign actual farmer components to groups:
        assigned = 0
        # first assign warrior spawn farmers
        for i in range(villagers_for_warrior_spawn):
            if assigned < n_farmers:
                environment.assign_group(farmers[assigned], SPAWN_WARRIOR)
                assigned += 1

        # then assign farmer spawn farmers
        for i in range(villagers_for_farmer_spawn):
            if assigned < n_farmers:
                environment.assign_group(farmers[assigned], SPAWN_FARMER)
                assigned += 1

        # remaining farmers farm
        while assigned < n_farmers:
            environment.assign_group(farmers[assigned], FARM)
            assigned += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group names expected:
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for comp in components:
            role = getattr(comp, "role", "").lower()
            # All warriors in the cave should attack
            if role == "warrior":
                environment.assign_group(comp, ATTACK)
            # Farmers in the cave should return to village to farm/spawn
            elif role == "farmer":
                environment.assign_group(comp, VILLAGE)
            else:
                # Default: keep them in cave (safe fallback)
                environment.assign_group(comp, CAVE)