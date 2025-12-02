from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available for spawning
        wheat = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            wheat = getattr(farm_env, "wheat", 0)

        # Strategy: keep at least 1 farmer farming if possible
        keep_farm = 1 if len(farmers) > 0 else 0
        available_for_spawns = max(0, len(farmers) - keep_farm)

        # Max spawns we can attempt this step
        max_farm_spawns = min(available_for_spawns // 2, wheat // 10)

        remaining_wheat = wheat - max_farm_spawns * 10
        remaining_farmers_after_farm_spawns = len(farmers) - 2 * max_farm_spawns

        max_war_spawns = min(remaining_farmers_after_farm_spawns // 2, remaining_wheat // 12)

        # Assign Farmers to spawn groups (spawn farmer first, then spawn warrior)
        idx = 0
        for f in farmers[:2 * max_farm_spawns]:
            environment.assign_group(f, "spawn farmer")
        idx += 2 * max_farm_spawns

        for f in farmers[idx: idx + 2 * max_war_spawns]:
            environment.assign_group(f, "spawn warrior")
        idx += 2 * max_war_spawns

        # Remaining farmers go to farm
        for f in farmers[idx:]:
            environment.assign_group(f, "farm")

        # All Warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack, Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")