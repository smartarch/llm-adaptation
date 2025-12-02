from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # Step 1: Send all Warriors to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Step 2: Handle Farmers in Village
        # If there are no farmers, nothing to do further
        if not farmers:
            return

        # Read wheat available in the Farm
        farm = getattr(environment, "farm", None)
        wheat = getattr(farm, "wheat", 0) if farm is not None else 0

        num_farmers = len(farmers)

        # Compute possible spawns greedily
        max_spawns_farmers = min(num_farmers // 2, wheat // 10)
        wheat_after_farm_spawns = wheat - (10 * max_spawns_farmers)

        remaining_farmers = num_farmers - (2 * max_spawns_farmers)

        max_spawns_warriors = min(remaining_farmers // 2, wheat_after_farm_spawns // 12)
        wheat_after_war_spawns = wheat_after_farm_spawns - (12 * max_spawns_warriors)

        # Assign farmers to groups
        idx = 0
        # 2 * max_spawns_farmers farmers go to "spawn farmer"
        for _ in range(2 * max_spawns_farmers):
            if idx < num_farmers:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # 2 * max_spawns_warriors farmers go to "spawn warrior"
        for _ in range(2 * max_spawns_warriors):
            if idx < num_farmers:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farming
        while idx < num_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, assign Warriors to attack, Farmers back to Village
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # Warriors attack
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers should go back to Village
        for f in farmers:
            environment.assign_group(f, "village")

        # If any other types exist (unexpected), default them to cave to keep them safe,
        # though the problem statement does not require this path.
        for c in components:
            r = getattr(c, "role", "").lower()
            if r not in ("warrior", "farmer"):
                environment.assign_group(c, "cave")