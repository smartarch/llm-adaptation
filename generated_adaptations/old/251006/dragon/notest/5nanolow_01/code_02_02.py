from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        num_farmers = len(farmers)
        farm_wheat = getattr(environment.farm, "wheat", 0)

        # Strategy:
        # 1) Spawn warriors as much as possible using farmers and wheat
        # 2) Then spawn farmers with remaining resources
        # 3) Remaining farmers stay farming
        # We must ensure all villagers are assigned to exactly one group.

        # Compute how many spawn-w Warrior groups we can form
        max_spawn_warriors = min(num_farmers // 2, farm_wheat // 12)

        # After allocating for spawn-warrior, compute remaining wheat
        wheat_after_warrior_spawns = farm_wheat - max_spawn_warriors * 12

        # Compute how many spawn-farmer groups we can form with the remaining resources
        max_spawn_farmers = min((num_farmers - max_spawn_warriors * 2) // 2, wheat_after_warrior_spawns // 10)

        # Assign farmers to spawn warrior group
        farmers_for_warrior_spawn = farmers[: 2 * max_spawn_warriors]
        # Assign farmers for spawn farmer group (from the remaining farmers)
        idx_after_warrior = 2 * max_spawn_warriors
        farmers_for_farm_spawn = farmers[idx_after_warrior: idx_after_warrior + (2 * max_spawn_farmers)]
        # Remaining farmers go to farming
        idx_after_farm_spawn = idx_after_warrior + 2 * max_spawn_farmers
        remaining_farmers = farmers[idx_after_farm_spawn:]

        # Assign to groups
        for c in farmers_for_warrior_spawn:
            environment.assign_group(c, "spawn warrior")
        for c in farmers_for_farm_spawn:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # All Warriors should go to the Cave (attack); ensure none left in village
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Split into Warriors (to attack) and Farmers (stay in village)
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # All Warriors go to the "attack" group
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers should stay in Village; send them to "village" group
        for f in farmers:
            environment.assign_group(f, "village")