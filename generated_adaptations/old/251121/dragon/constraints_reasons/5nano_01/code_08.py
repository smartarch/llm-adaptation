from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_village = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Rule: All warriors should go to the Cave
        for w in warriors_in_village:
            environment.assign_group(w, "cave")

        f_count = len(farmers)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawning decision (maximize spawns given wheat and farmers)
        s_farm_spawns = 0
        if f_count >= 2 and wheat >= 10:
            s_farm_spawns = min(f_count // 2, wheat // 10)

        # After farmer spawns, compute remaining wheat and farmers
        wheat_after_farm = wheat - s_farm_spawns * 10
        remaining_farmers_for_war = f_count - s_farm_spawns * 2

        s_war_spawns = 0
        if remaining_farmers_for_war >= 2 and wheat_after_farm >= 12:
            s_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)

        # Build sets of farmers assigned to spawn
        spawn_farm_set = set()
        spawn_war_set = set()

        idx = 0
        # choose first 2*s_farm_spawns farmers for farmer-spawns
        for _ in range(s_farm_spawns * 2):
            spawn_farm_set.add(farmers[idx])
            idx += 1
        # next 2*s_war_spawns farmers for warrior-spawns
        for _ in range(s_war_spawns * 2):
            spawn_war_set.add(farmers[idx])
            idx += 1

        # Assign all farmers based on these sets (per-component mapping)
        for c in farmers:
            if c in spawn_farm_set:
                environment.assign_group(c, "spawn farmer")
            elif c in spawn_war_set:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

        # For any non-Farmer/Warrior components in village, assign to farm by default
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Classify villagers in the Cave
        farmers_in_cave = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Farmers should go to the Village
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # Warriors: maximize DPS by attacking with all warriors
        for w in warriors_in_cave:
            environment.assign_group(w, "attack")

        # Unknown-role villagers: default to cave
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "cave")