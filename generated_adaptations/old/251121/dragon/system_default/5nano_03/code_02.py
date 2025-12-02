from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers currently in the Village into spawn groups, farming, and moving Warriors to cave.
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available for spawning decisions
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Max spawns we can attempt given current counts and wheat
        max_spawn_farmers = min(len(farmers) // 2, wheat // 10)  # number of Farmer spawns (pairs)
        remaining_wheat_after_farm = wheat - max_spawn_farmers * 10
        remaining_farmers_after_farm_spawns = len(farmers) - 2 * max_spawn_farmers

        max_spawn_warriors = min(remaining_farmers_after_farm_spawns // 2, remaining_wheat_after_farm // 12)  # spawn Warriors

        # Assign farmers to spawn groups and farm group
        # First 2*max_spawn_farmers farmers -> spawn farmer group
        for f in farmers[: 2 * max_spawn_farmers]:
            environment.assign_group(f, "spawn farmer")

        # Next 2*max_spawn_warriors farmers -> spawn warrior group
        idx_start_war = 2 * max_spawn_farmers
        for f in farmers[idx_start_war: idx_start_war + 2 * max_spawn_warriors]:
            environment.assign_group(f, "spawn warrior")

        # Remaining farmers -> farm
        idx_start_farm = 2 * max_spawn_farmers + 2 * max_spawn_warriors
        for f in farmers[idx_start_farm:]:
            environment.assign_group(f, "farm")

        # All Warriors should go to the Cave (to prepare for attack)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should head back to Village
                environment.assign_group(c, "village")