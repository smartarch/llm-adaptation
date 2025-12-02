from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": stay in Village to farm
        - "cave": go to the Cave (to join the attack later)
        - "spawn farmer": for every two villagers assigned and 10 wheat, spawn a new Farmer
        - "spawn warrior": for every two villagers assigned and 12 wheat, spawn a new Warrior
        Strategy:
        - Move all Warriors to "cave" (to head to the Cave)
        - Use Farmers to populate "spawn farmer" and "spawn warrior" groups based on available wheat
        - Remaining Farmers go to "farm"
        """
        # Collect indices by role
        farmer_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Farmer"]
        warrior_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Warrior"]

        # Track assigned indices to avoid duplicates
        assigned = set()

        # Wheat available for spawning
        available_wheat = getattr(environment.farm, "wheat", 0)

        # 1) Spawn farmers (prefer up to 2 spawns)
        max_farm_spawns = min(len(farmer_indices) // 2, available_wheat // 10)
        spawn_farm_count = min(2, max_farm_spawns)

        spawn_farm_indices = farmer_indices[:2 * spawn_farm_count]
        assigned.update(spawn_farm_indices)

        remaining_farmers_after_farm_spawns = farmer_indices[2 * spawn_farm_count:]

        # Update wheat after spawning farmers
        available_wheat -= spawn_farm_count * 10

        # 2) Spawn warriors from remaining farmers (prefer up to 2 spawns)
        max_warrior_spawns = min(len(remaining_farmers_after_farm_spawns) // 2, available_wheat // 12)
        spawn_warrior_count = min(2, max_warrior_spawns)

        spawn_warrior_indices = remaining_farmers_after_farm_spawns[:2 * spawn_warrior_count]
        assigned.update(spawn_warrior_indices)

        remaining_farmers = remaining_farmers_after_farm_spawns[2 * spawn_warrior_count:]
        assigned.update(remaining_farmers)

        # 3) Assign groups
        # Farmers allocated to spawn groups
        for idx in spawn_farm_indices:
            environment.assign_group(components[idx], "spawn farmer")

        for idx in spawn_warrior_indices:
            environment.assign_group(components[idx], "spawn warrior")

        # Farmers who remain (not spawning) stay in farm
        for idx in remaining_farmers:
            environment.assign_group(components[idx], "farm")

        # Warriors (all go to cave to prepare for attack)
        for idx in warrior_indices:
            environment.assign_group(components[idx], "cave")

        # If any component wasn't assigned (shouldn't happen), default them to farming
        for i, c in enumerate(components):
            if i not in assigned:
                # Safety fallback
                if getattr(c, "role", None) == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village
        Strategy:
        - Move all Warriors to "attack" (they will attack Dragon)
        - Move all Farmers to "village" (they stay in Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:  # Farmer
                environment.assign_group(c, "village")