from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers when they are in the Village.

        Strategy:
        - All Warriors go to the Cave (group "cave").
        - Farmers may be assigned to:
          - "spawn farmer" in pairs to spawn new Farmers (consumes 10 wheat per spawn),
          - "spawn warrior" in pairs to spawn new Warriors (consumes 12 wheat per spawn),
          - the rest to "farm" to produce more wheat.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to cave (to go to the Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning for Farmers
        available_wheat = getattr(environment.farm, "wheat", 0)

        # Number of possible farmer spawns given wheat
        max_farmer_spawns = available_wheat // 10 if available_wheat >= 10 else 0
        # Each spawn requires 2 farmers in the group
        possible_farmer_pairs = len(farmers) // 2
        farmer_spawns = min(max_farmer_spawns, possible_farmer_pairs)

        # Assign 2 * farmer_spawns farmers to "spawn farmer"
        num_to_spawn_farmers = farmer_spawns * 2
        spawn_farmers_candidates = farmers[:num_to_spawn_farmers]
        for c in spawn_farmers_candidates:
            environment.assign_group(c, "spawn farmer")

        remaining_farmers_after_farmers = farmers[num_to_spawn_farmers:]

        # Wheat left after farmer spawns (assuming 10 wheat per spawn)
        wheat_after_farmers = available_wheat - (farmer_spawns * 10)
        # Recompute how many warrior spawns we can support with remaining wheat
        max_warrior_spawns = 0
        if wheat_after_farmers >= 12 and len(remaining_farmers_after_farmers) >= 2:
            max_warrior_spawns = min(len(remaining_farmers_after_farmers) // 2, wheat_after_farmers // 12)

        # Assign 2 * max_warrior_spawns farmers to "spawn warrior"
        num_to_spawn_warriors = max_warrior_spawns * 2
        spawn_warriors_candidates = remaining_farmers_after_farmers[:num_to_spawn_warriors]
        for c in spawn_warriors_candidates:
            environment.assign_group(c, "spawn warrior")

        remaining_farmers = remaining_farmers_after_farmers[num_to_spawn_warriors:]

        # 3) The rest of Farmers go to the "farm" group
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # Note: If there are farmers and some wheat, this will spawn as many as possible
        # but we keep the logic simple and deterministic.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers when they are in the Cave.

        Strategy:
        - Warriors go to "attack" to fight the Dragon.
        - Farmers go to "village" to return and continue farming/spawning.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (or any other role) go back to village
                environment.assign_group(c, "village")
        # The "cave" group in cave phase is not used here since all farmers return to village
        # and all warriors attack from the cave.