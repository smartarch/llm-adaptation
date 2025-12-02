from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    """
    Improved strategy:
    - Send all warriors in the village to the cave.
    - Farmers stay in village: either farm or join spawn groups.
      * If wheat >= 12 and there are at least 2 farmers, allow spawning warriors (do not forcibly keep one farmer).
      * Otherwise, keep at least one farmer farming to accumulate wheat.
      * Prioritize warrior spawns (cost 12) then farmer spawns (cost 10).
    - In cave: warriors attack; farmers return to village.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Partition villagers
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # Send all warriors to the Cave
        for w in warriors:
            environment.assign_group(w, CAVE)

        n_farmers = len(farmers)
        wheat = int(getattr(environment.farm, "wheat", 0))

        # If we have at least 2 farmers and at least 12 wheat, allow spawning warriors
        # (do not force keeping one farmer). Otherwise keep at least one farmer farming.
        if n_farmers >= 2 and wheat >= 12:
            min_farmers_kept = 0
        else:
            min_farmers_kept = 1 if n_farmers > 0 else 0

        available_for_spawn = max(0, n_farmers - min_farmers_kept)

        # Prioritize warrior spawns (cost 12 wheat, 2 villagers per spawn)
        max_warrior_spawns_by_wheat = wheat // 12
        max_warrior_spawns_by_people = available_for_spawn // 2
        warrior_spawns_to_do = min(max_warrior_spawns_by_wheat, max_warrior_spawns_by_people)

        villagers_for_warrior_spawn = warrior_spawns_to_do * 2
        wheat_after_warrior_spawns = wheat - (warrior_spawns_to_do * 12)
        available_for_spawn -= villagers_for_warrior_spawn

        # Then farmer spawns (cost 10 wheat, 2 villagers per spawn)
        max_farmer_spawns_by_wheat = wheat_after_warrior_spawns // 10
        max_farmer_spawns_by_people = available_for_spawn // 2
        farmer_spawns_to_do = min(max_farmer_spawns_by_wheat, max_farmer_spawns_by_people)

        villagers_for_farmer_spawn = farmer_spawns_to_do * 2

        # Assign farmers to groups in order: warrior spawn, farmer spawn, then farm
        assigned = 0
        # warrior spawns
        for i in range(villagers_for_warrior_spawn):
            if assigned < n_farmers:
                environment.assign_group(farmers[assigned], SPAWN_WARRIOR)
                assigned += 1

        # farmer spawns
        for i in range(villagers_for_farmer_spawn):
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
                environment.assign_group(comp, ATTACK)
            elif role == "farmer":
                # Farmers shouldn't stay in cave; send them back to village
                environment.assign_group(comp, VILLAGE)
            else:
                # Fallback: keep in cave
                environment.assign_group(comp, CAVE)