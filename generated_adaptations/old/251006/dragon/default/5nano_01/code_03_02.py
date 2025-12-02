from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # 1) All Warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        num_farmers = len(farmers)
        if num_farmers == 0:
            return

        # Wheat available for spawning (robust to missing farm information)
        farm = getattr(environment, "farm", None)
        wheat = getattr(farm, "wheat", 0) if farm is not None else 0

        # Stage-based spawning strategy
        if step < 5:
            # Stage 0: focus on farming; assign all farmers to farming
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Stage 1+: aggressive but controlled spawns to boost early dragon damage
        # Compute maximum warrior spawns (need 2 farmers and 12 wheat per Warrior)
        max_war_spawns = min(num_farmers // 2, wheat // 12)

        # Remaining farmers and wheat after Warrior spawns
        remaining_farmers = num_farmers - (2 * max_war_spawns)
        wheat_after_war_spawns = wheat - (12 * max_war_spawns)

        # Compute maximum farmer spawns with the remaining resources
        max_farm_spawns = min(remaining_farmers // 2, wheat_after_war_spawns // 10)

        # Assign groups accordingly
        idx = 0
        # 2 * max_war_spawns farmers -> spawn warrior
        for _ in range(max_war_spawns * 2):
            if idx < num_farmers:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # 2 * max_farm_spawns farmers -> spawn farmer
        for _ in range(max_farm_spawns * 2):
            if idx < num_farmers:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers -> farming
        while idx < num_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack and move Farmers back to Village
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # Warriors attack
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers should go back to Village
        for f in farmers:
            environment.assign_group(f, "village")

        # If there are any other roles, default them to cave (safety)
        for c in components:
            r = getattr(c, "role", "").lower()
            if r not in ("warrior", "farmer"):
                environment.assign_group(c, "cave")