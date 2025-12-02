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

        # Max warrior spawns this turn given available farmers and wheat
        max_warrior_spawns = min(F // 2, wheat // 12)
        max_warrior_spawns = max(0, max_warrior_spawns)

        wheat_after_war_spawns = wheat - max_warrior_spawns * 12
        farmers_after_war_spawns = F - max_warrior_spawns * 2

        # Max farmer spawns this turn after warrior spawns
        max_farm_spawns = min(farmers_after_war_spawns // 2, wheat_after_war_spawns // 10)
        max_farm_spawns = max(0, max_farm_spawns)

        # Allocate farmers to spawn groups
        # Warriors spawn first
        to_spawn_warriors = farmers[:2 * max_warrior_spawns]
        start_war = 2 * max_warrior_spawns
        to_spawn_farmers = farmers[start_war: start_war + 2 * max_farm_spawns]
        to_farm = farmers[start_war + 2 * max_farm_spawns:]

        for c in to_spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in to_spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in to_farm:
            environment.assign_group(c, "farm")

        # Safety: any remaining farmers not assigned to spawns go to farm
        assigned = set(to_spawn_warriors) | set(to_spawn_farmers) | set(to_farm)
        for c in farmers:
            if c not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")