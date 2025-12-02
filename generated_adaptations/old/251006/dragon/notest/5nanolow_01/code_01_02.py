from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy:
        # - All Warriors: will go to the Cave (handled in assign_in_cave)
        # - Farmers: stay in Village and farm by default
        # - Spawn farmers: convert as many farmer pairs as possible into "spawn farmer",
        #   limited by available wheat (10 wheat per spawn)
        farm_wheat = getattr(environment.farm, "wheat", 0)

        num_farmers = len(farmers)
        max_possible_spawns = min(num_farmers // 2, farm_wheat // 10)

        # Assign farmers to "spawn farmer" for the required number of spawns
        # We take the first 2*max_possible_spawns farmers to form spawn groups
        farmers_for_spawn = farmers[: 2 * max_possible_spawns]
        remaining_farmers = farmers[2 * max_possible_spawns:]

        # Assign to groups
        for c in farmers_for_spawn:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # All Warriors should go to the Cave (handled in assign_in_cave),
        # but at village stage, ensure we don't assign them to any village-specific group.
        # If any Warrior accidentally remains, assign them to "cave" as a safe default.
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Split into Warriors (to attack) and Farmers (stay in village)
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # All Warriors go to the "attack" group
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers stay in the Village; assign them to "village" group
        for f in farmers:
            environment.assign_group(f, "village")