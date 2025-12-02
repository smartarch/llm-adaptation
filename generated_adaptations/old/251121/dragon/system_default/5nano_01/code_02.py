from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Compute how many spawns we can trigger this step
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        remaining_wheat_after_farm = max(0, wheat - max_farm_spawns * 10)

        remaining_farmers_after_farm_spawns = len(farmers) - (max_farm_spawns * 2)

        max_warrior_spawns = min(remaining_farmers_after_farm_spawns // 2,
                                 remaining_wheat_after_farm // 12)

        # Assign groups for Farmers
        # First, 2*max_farm_spawns Farmers to "spawn farmer"
        farm_spawn_farmers = farmers[:2 * max_farm_spawns]
        # Next, 2*max_warrior_spawns Farmers to "spawn warrior"
        warrior_spawn_start = 2 * max_farm_spawns
        farm_spawn_warriors = farmers[warrior_spawn_start: warrior_spawn_start + 2 * max_warrior_spawns]
        # Remaining farmers go to farming
        farm_farmers = farmers[warrior_spawn_start + 2 * max_warrior_spawns:]

        # Assign groups for Farmers
        for c in farm_spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        for c in farm_spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        for c in farm_farmers:
            environment.assign_group(c, "farm")

        # Assign all Warriors to the cave (to go attack later)
        for c in warriors:
            environment.assign_group(c, "cave")

        # If there are any remaining villagers (edge case), ensure they go somewhere sensible
        # For safety, send any remaining farmers (if any were not listed above) to farming
        # (Not strictly necessary due to slicing above, but harmless)
        assigned = set(farm_spawn_farmers) | set(farm_spawn_warriors) | set(farm_farmers) | set(warriors)
        for c in components:
            if c not in assigned and getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "farm")

        # Note: Farmers going to "cave" is not desired; Warriors are the only ones that should head to the cave.
        # The "spawn" groups inherently keep a portion of Farmers growing the village.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")