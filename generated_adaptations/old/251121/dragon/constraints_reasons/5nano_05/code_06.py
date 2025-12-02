from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": stay in Village to farm
        - "cave": go to the Cave
        - "spawn farmer": for every two villagers assigned and 10 wheat, spawn a new Farmer
        - "spawn warrior": for every two villagers assigned and 12 wheat, spawn a new Warrior
        Strategy:
        - Move all Warriors to "cave" (to head to the Cave)
        - Spawn as many Farmers as possible given wheat, while reserving a couple of Farmers for ongoing farming
        - Then spawn as many Warriors as possible from remaining Farmers
        - Remaining Farmers go to "farm"
        - All Farmers in Village who aren't spawning stay in farm; all Warriors go to cave
        - Ensure every component is assigned exactly once
        """
        # Collect indices by role
        farmer_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Farmer"]
        warrior_indices = [i for i, c in enumerate(components) if getattr(c, "role", None) == "Warrior"]

        total_farmers = len(farmer_indices)
        assigned = set()

        # Wheat available for spawning
        available_wheat = getattr(environment.farm, "wheat", 0)

        # Reserve some farmers to keep farming (minimum 2 if available)
        reserve = 2 if total_farmers >= 2 else total_farmers

        # Spawn as many farmers as possible given wheat and available farmers to spawn
        max_farm_spawns = min((total_farmers - reserve) // 2, available_wheat // 10)
        spawn_farm_count = max(0, max_farm_spawns)

        spawn_farm_indices = farmer_indices[:2 * spawn_farm_count]
        for idx in spawn_farm_indices:
            environment.assign_group(components[idx], "spawn farmer")
        assigned.update(spawn_farm_indices)
        available_wheat -= spawn_farm_count * 10

        # After spawning farmers, compute remaining farmers and spawn warriors if possible
        remaining_farmers_after_farm = [idx for idx in farmer_indices if idx not in assigned]

        max_warrior_spawns = min(len(remaining_farmers_after_farm) // 2, available_wheat // 12)
        spawn_warrior_count = max(0, max_warrior_spawns)

        spawn_warrior_indices = remaining_farmers_after_farm[:2 * spawn_warrior_count]
        for idx in spawn_warrior_indices:
            environment.assign_group(components[idx], "spawn warrior")
        assigned.update(spawn_warrior_indices)
        available_wheat -= spawn_warrior_count * 12

        # Remaining farmers (not spawning) stay in village (farm)
        remaining_farmers = [idx for idx in farmer_indices if idx not in assigned]
        for idx in remaining_farmers:
            environment.assign_group(components[idx], "farm")
        assigned.update(remaining_farmers)

        # All Warriors go to cave (to attack)
        for idx in warrior_indices:
            environment.assign_group(components[idx], "cave")
        assigned.update(warrior_indices)

        # Safety: ensure every component is assigned (edge cases)
        for i, c in enumerate(components):
            if i not in assigned:
                if getattr(c, "role", None) == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
                assigned.add(i)

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
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")