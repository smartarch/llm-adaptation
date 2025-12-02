from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Ensure all Warriors move to the Cave to attack (as required)
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")

        # Gather all Farmers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]

        # Wheat available for spawning decisions
        wheat = int(environment.farm.wheat)

        # Number of possible new Farmers we can spawn now:
        # For each new Farmer spawned, we need 2 existing villagers in the spawn group and 10 wheat.
        # We approximate by using the number of Farmers we have as potential spawn participants.
        possible_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Total number of Farmers to assign to the "spawn farmer" group
        spawn_farmers_to_assign = 2 * possible_farm_spawns

        # Update wheat after allocating for farming spawns
        wheat_left_after_farm_spawns = wheat - (10 * possible_farm_spawns)

        # Remaining farmers after allocating to spawn farmer group
        remaining_farmers_after_farm_spawns = farmers[spawn_farmers_to_assign:]

        # Possible Warrior spawns using remaining farmers and remaining wheat
        possible_war_spawns = min(len(remaining_farmers_after_farm_spawns) // 2,
                                  wheat_left_after_farm_spawns // 12)

        spawn_warriors_to_assign = 2 * possible_war_spawns

        # Assign farmers to groups
        for i, f in enumerate(farmers):
            if i < spawn_farmers_to_assign:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmers_to_assign + spawn_warriors_to_assign:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, keep Warriors in the "attack" group; Farmers go to the Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")