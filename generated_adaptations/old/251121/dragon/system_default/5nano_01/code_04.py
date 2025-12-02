from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers currently in the Village by role
        villagers_in_village = list(components)
        farmers = [c for c in villagers_in_village if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in villagers_in_village if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave to start attacking immediately
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning using current wheat
        wheat = getattr(environment.farm, "wheat", 0)

        F = len(farmers)

        # Maximum number of "spawn farmer" actions this turn
        max_farm_spawns = min(F // 2, wheat // 10)
        max_farm_spawns = max(0, max_farm_spawns)

        wheat_after_farm_spawns = wheat - max_farm_spawns * 10
        farmers_after_farm_spawns = F - max_farm_spawns * 2

        # Maximum number of "spawn warrior" actions this turn after farmer spawns
        max_warrior_spawns = min(farmers_after_farm_spawns // 2, wheat_after_farm_spawns // 12)
        max_warrior_spawns = max(0, max_warrior_spawns)

        # Assign farmers to appropriate spawn groups
        # First 2*max_farm_spawns farmers to "spawn farmer"
        to_spawn_farmers = farmers[:2 * max_farm_spawns]
        # Next 2*max_warrior_spawns farmers to "spawn warrior"
        start_war = 2 * max_farm_spawns
        to_spawn_warriors = farmers[start_war: start_war + 2 * max_warrior_spawns]
        # Remaining farmers go to farming
        to_farm = farmers[start_war + 2 * max_warrior_spawns:]

        for c in to_spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in to_farm:
            environment.assign_group(c, "farm")

        # Safety: if any Farmer remains unassigned (edge case), send them to farm
        assigned = set(to_spawn_farmers) | set(to_spawn_warriors) | set(to_farm)
        for c in villagers_in_village:
            if c not in assigned and getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")