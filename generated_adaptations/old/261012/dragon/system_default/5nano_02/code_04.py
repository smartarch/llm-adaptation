from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Start attacking by sending a small number of Farmers to the Cave.
        # - Use Wheat to spawn Farmers first, then Warriors, using pairs of villagers.
        # - Leave any remaining villagers in Farm.

        mapping = {}

        # Step 1: initial attack push - move up to 3 Farmers to cave to start dealing damage
        # (if there are fewer than 3 villagers, move as many as available)
        initial_attackers = min(3, len(components))
        for i, c in enumerate(components):
            if i < initial_attackers:
                mapping[c] = "cave"  # go to Cave and attack as Farmers (attack power 1)
            else:
                mapping[c] = "farm"

        # Step 2: spawning planning based on wheat in farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = getattr(environment.farm, "wheat", 0)

        # Pool of villagers available for spawning (those not currently assigned to cave)
        farmers_for_spawn = [c for c in components if mapping.get(c) != "cave"]

        # Spawn Farmer: needs 2 villagers in spawn farmer and 10 wheat
        max_farm_spawns_by_wheat = wheat // 10
        max_farm_spawns_by_count = len(farmers_for_spawn) // 2
        max_farm_spawns = min(max_farm_spawns_by_wheat, max_farm_spawns_by_count)

        # Assign 2 villagers per Farmer spawn to "spawn farmer"
        idx = 0
        for _ in range(max_farm_spawns):
            if idx + 1 < len(farmers_for_spawn):
                a = farmers_for_spawn[idx]
                b = farmers_for_spawn[idx + 1]
                mapping[a] = "spawn farmer"
                mapping[b] = "spawn farmer"
                idx += 2
            else:
                break

        # Recompute wheat after farmer spawns
        wheat_after_farm_spawns = wheat - max_farm_spawns * 10
        if wheat_after_farm_spawns < 0:
            wheat_after_farm_spawns = 0

        # Spawn Warrior: needs 2 villagers in spawn warrior and 12 wheat
        remaining_for_warrior = [c for c in components if mapping.get(c) != "spawn farmer" and mapping.get(c) != "cave"]
        # Those remaining_for_warrior are effectively in "farm" now

        max_warrior_spawns_by_wheat = wheat_after_farm_spawns // 12
        max_warrior_spawns_by_count = len(remaining_for_warrior) // 2
        max_warrior_spawns = min(max_warrior_spawns_by_wheat, max_warrior_spawns_by_count)

        idx = 0
        for _ in range(max_warrior_spawns):
            if idx + 1 < len(remaining_for_warrior):
                a = remaining_for_warrior[idx]
                b = remaining_for_warrior[idx + 1]
                mapping[a] = "spawn warrior"
                mapping[b] = "spawn warrior"
                idx += 2
            else:
                break

        # Ensure any villager not yet assigned gets a default grouping
        for c in components:
            if c not in mapping:
                mapping[c] = "farm"

        # Apply the group assignments
        for component, gid in mapping.items():
            environment.assign_group(component, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - Warriors should attack the Dragon
        # - Farmers should return to the Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")