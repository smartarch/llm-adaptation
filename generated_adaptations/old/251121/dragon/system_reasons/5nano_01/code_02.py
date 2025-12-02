from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Move all Warriors to the cave (group "cave").
        - Farmers stay in village (group "farm") by default.
        - Spawn farmers and/or warriors using the two spawn groups, based on available wheat and the number of farmers.
        - For spawning:
            - To spawn k new Farmers: assign 2k Farmers to "spawn farmer" and consume 10k Wheat.
            - To spawn m new Warriors: assign 2m Farmers to "spawn warrior" and consume 12m Wheat.
        - The remaining Farmers go to the "farm" group.
        """
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawn planning: decide how many to spawn, constrained by available farmers and wheat
        f_count = len(farmers)

        # Max possible farmer spawns given number of farmers (need 2 per new farmer) and wheat (10 per new)
        max_farm_spawns = 0
        if f_count >= 2 and wheat >= 10:
            max_farm_spawns = min(f_count // 2, wheat // 10)

        # After allocating farmer-spawn, compute remaining wheat and farmers
        spawn_farm_n = max_farm_spawns  # number of new farmers to attempt to spawn
        wheat_after_farm = wheat - (spawn_farm_n * 10)
        remaining_farmers_after_farm_spawns = f_count - (spawn_farm_n * 2)

        # Max possible warrior spawns: need 2 farmers per new warrior, and 12 wheat per new
        max_war_spawns = 0
        if remaining_farmers_after_farm_spawns >= 2 and wheat_after_farm >= 12:
            max_war_spawns = min(remaining_farmers_after_farm_spawns // 2, wheat_after_farm // 12)

        spawn_war_n = max_war_spawns  # number of new warriors to spawn
        wheat_after_war = wheat_after_farm - (spawn_war_n * 12)

        # Assign groups:
        # 1) Warriors go to cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers allocations for spawning or farming
        used_for_farm_spawns = set()
        used_for_war_spawns = set()

        # Assign first 2*spawn_farm_n farmers to "spawn farmer"
        if spawn_farm_n > 0:
            to_spawn_farm = farmers[:2 * spawn_farm_n]
            for c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")
            used_for_farm_spawns.update(to_spawn_farm)

        # Assign next 2*spawn_war_n farmers to "spawn warrior" (if any)
        if spawn_war_n > 0:
            start = 2 * spawn_farm_n
            end = start + (2 * spawn_war_n)
            to_spawn_war = farmers[start:end]
            for c in to_spawn_war:
                environment.assign_group(c, "spawn warrior")
            used_for_war_spawns.update(to_spawn_war)

        # The remaining farmers go to farming in village
        for c in farmers:
            if c in used_for_farm_spawns or c in used_for_war_spawns:
                continue
            environment.assign_group(c, "farm")

        # Any non-Farmer, non-Warrior components: stay in village (default to farm)
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors should attack the Dragon: assign to "attack".
        - Farmers should go back to the Village: assign to "village".
        """
        for v in components:
            role = getattr(v, "role", None)
            if role == "Warrior":
                environment.assign_group(v, "attack")
            else:
                # Farmers and any other roles go to the Village
                environment.assign_group(v, "village")