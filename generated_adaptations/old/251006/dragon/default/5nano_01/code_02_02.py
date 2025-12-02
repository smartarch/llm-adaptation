from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # All Warriors should head to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        num_farmers = len(farmers)
        if num_farmers == 0:
            return

        # Wheat available for spawning (best-effort: default to 0 if not present)
        farm = getattr(environment, "farm", None)
        wheat = getattr(farm, "wheat", 0) if farm is not None else 0

        # Spawn decisions with per-step caps to avoid explosion
        # Limit to at most 2 farmer-spawns this step
        spawns_farmers = min(num_farmers // 2, wheat // 10, 2)
        wheat_after_farm_spawns = wheat - (spawns_farmers * 10)

        # Limit to at most 1 warrior-spawn this step (to seed early attacking force)
        remaining_farmers_after_farm_spawns = num_farmers - (2 * spawns_farmers)
        spawns_warriors = 0
        if remaining_farmers_after_farm_spawns > 0 and wheat_after_farm_spawns >= 12:
            spawns_warriors = min(remaining_farmers_after_farm_spawns // 2, wheat_after_farm_spawns // 12, 1)

        # Assign specific farmers to spawn groups, then the rest to farming
        idx = 0

        # 2 * spawns_farmers farmers go to "spawn farmer"
        for _ in range(spawns_farmers * 2):
            if idx < num_farmers:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # 2 * spawns_warriors farmers go to "spawn warrior"
        for _ in range(spawns_warriors * 2):
            if idx < num_farmers:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers go to farming
        while idx < num_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack and move Farmers back to Village
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        for w in warriors:
            environment.assign_group(w, "attack")

        for f in farmers:
            environment.assign_group(f, "village")

        # Any other types (if present) can default to cave (safety)
        for c in components:
            r = getattr(c, "role", "").lower()
            if r not in ("warrior", "farmer"):
                environment.assign_group(c, "cave")