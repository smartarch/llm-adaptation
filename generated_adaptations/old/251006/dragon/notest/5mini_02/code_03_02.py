from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    """
    Balanced strategy to preserve field activity while spawning enough warriors:
    - All warriors -> Cave (and attack there).
    - Farmers in Village: keep a farming reserve (at least 2 if possible),
      but allow warrior spawns when wheat is available. If wheat is abundant
      after warrior spawns, spawn some farmers to grow the farming base.
    - Farmers in Cave -> return to Village.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # Send all warriors in the Village to the Cave
        for w in warriors:
            environment.assign_group(w, CAVE)

        n_farmers = len(farmers)
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Decide how many farmers to keep farming (reserve)
        # - If 3+ farmers: keep at least 2 farming to maintain steady wheat production
        # - If 1-2 farmers: allow spawning only if there's already wheat (to avoid starving),
        #   otherwise keep 1 farming.
        if n_farmers >= 3:
            min_farmers_kept = 2
        elif n_farmers == 2:
            min_farmers_kept = 0 if wheat >= 12 else 1
        elif n_farmers == 1:
            min_farmers_kept = 0 if wheat >= 12 else 1
        else:
            min_farmers_kept = 0

        # Ensure we don't request keeping more farmers than exist
        min_farmers_kept = min(min_farmers_kept, n_farmers)

        available_for_spawn = max(0, n_farmers - min_farmers_kept)

        # Prioritize warrior spawns (cost 12 wheat, 2 villagers per spawn)
        max_warrior_spawns_by_wheat = wheat // 12
        max_warrior_spawns_by_people = available_for_spawn // 2
        warrior_spawns_to_do = min(max_warrior_spawns_by_wheat, max_warrior_spawns_by_people)

        villagers_for_warrior_spawn = warrior_spawns_to_do * 2
        wheat_after_warrior_spawns = wheat - (warrior_spawns_to_do * 12)
        available_for_spawn -= villagers_for_warrior_spawn

        # If there's a comfortable wheat surplus after warrior spawns, allow farmer spawns
        # Use a conservative threshold so we keep producing wheat: require surplus >= 20
        farmer_spawns_to_do = 0
        if available_for_spawn >= 2 and wheat_after_warrior_spawns >= 20:
            max_farmer_spawns_by_wheat = wheat_after_warrior_spawns // 10
            max_farmer_spawns_by_people = available_for_spawn // 2
            farmer_spawns_to_do = min(max_farmer_spawns_by_wheat, max_farmer_spawns_by_people)

        villagers_for_farmer_spawn = farmer_spawns_to_do * 2
        available_for_spawn -= villagers_for_farmer_spawn

        # Assign farmers to groups: warrior spawns first, then farmer spawns, then remaining farm
        assigned = 0
        # warrior spawns
        for _ in range(villagers_for_warrior_spawn):
            if assigned < n_farmers:
                environment.assign_group(farmers[assigned], SPAWN_WARRIOR)
                assigned += 1

        # farmer spawns
        for _ in range(villagers_for_farmer_spawn):
            if assigned < n_farmers:
                environment.assign_group(farmers[assigned], SPAWN_FARMER)
                assigned += 1

        # remaining farmers farm
        while assigned < n_farmers:
            environment.assign_group(farmers[assigned], FARM)
            assigned += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for comp in components:
            role = getattr(comp, "role", "").lower()
            if role == "warrior":
                # Warriors should always attack when in the cave
                environment.assign_group(comp, ATTACK)
            elif role == "farmer":
                # Farmers should not stay in cave; return to village
                environment.assign_group(comp, VILLAGE)
            else:
                # Fallback: keep in cave
                environment.assign_group(comp, CAVE)