from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village groups: "farm", "cave", "spawn farmer", "spawn warrior"
        Strategy:
        - Send a small target number of warriors to the Cave (1-3 depending on dragon HP and how many warriors we have).
        - Keep remaining warriors farming (they produce wheat too).
        - Keep at least two farmers farming (if available).
        - Use spare farmers in pairs to spawn 1 warrior per turn when possible (prioritize warrior spawn), and spawn farmers only if spare pairs & wheat remain.
        """
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Observables
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        # Determine target attackers (small strike force)
        num_warriors = len(warriors)
        if num_warriors == 0:
            target_attackers = 0
        else:
            # Scale modestly with dragon HP but cap to avoid mass exposure
            if dragon_hp > 40:
                target_attackers = min(3, num_warriors)
            elif dragon_hp > 20:
                target_attackers = min(2, num_warriors)
            else:
                target_attackers = min(1, num_warriors)

        # Choose which warriors to send (prefer higher HP to keep low-HP in reserve)
        sorted_warriors = sorted(warriors, key=lambda c: getattr(c, "hp", 0), reverse=True)
        attackers_set = set(sorted_warriors[:target_attackers])

        # Assign warriors: selected attackers -> cave, others -> farm (help produce wheat)
        for w in warriors:
            if w in attackers_set:
                environment.assign_group(w, CAVE)
            else:
                environment.assign_group(w, FARM)

        # Farmers: keep a reserve farming to produce wheat
        total_farmers = len(farmers)
        reserve_farmers = 2 if total_farmers >= 2 else total_farmers
        spare_farmers = max(0, total_farmers - reserve_farmers)
        spare_pairs = spare_farmers // 2

        # Decide spawning:
        # Prioritize spawning up to 1 warrior per turn if possible (steady growth),
        # allow more warrior spawns if wheat is abundant and many spare pairs exist.
        max_warriors_by_wheat = wheat // 12
        # Try to spawn at least one warrior if possible
        warrior_spawns = 0
        if spare_pairs >= 1 and max_warriors_by_wheat >= 1:
            # If wheat very high, allow up to spare_pairs spawns but cap to 2 to avoid starving farm
            warrior_spawns = min(spare_pairs, max_warriors_by_wheat, 2) if wheat >= 36 else 1

        farmers_for_warrior = warrior_spawns * 2
        wheat_after_warrior = wheat - warrior_spawns * 12
        spare_after = spare_farmers - farmers_for_warrior
        spare_pairs_after = spare_after // 2

        # Spawn farmers if we have spare pairs after warrior spawns and wheat remains
        farmer_spawns = min(spare_pairs_after, wheat_after_warrior // 10)

        farmers_for_farmer = farmer_spawns * 2

        # Assign farmer components to spawn groups or farm
        idx = 0
        # Assign farmers chosen for warrior spawn
        for _ in range(farmers_for_warrior):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], SPAWN_WARRIOR)
                idx += 1
        # Assign farmers chosen for farmer spawn
        for _ in range(farmers_for_farmer):
            if idx < total_farmers:
                environment.assign_group(farmers[idx], SPAWN_FARMER)
                idx += 1
        # Remaining farmers farm
        while idx < total_farmers:
            environment.assign_group(farmers[idx], FARM)
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave groups: "attack", "cave", "village"
        Strategy:
        - Warriors in the Cave attack.
        - Farmers in the Cave are sent back to the Village immediately.
        """
        ATTACK = "attack"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, ATTACK)
            else:
                # Send farmers back to village (they belong to farming/spawning roles)
                environment.assign_group(c, VILLAGE)