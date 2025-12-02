from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors should go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available at the farm
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Maximum possible farmer spawns this step: 2 farmers per spawn, 10 wheat per spawn
        if len(farmers) >= 2 and wheat >= 10:
            max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        else:
            max_farm_spawns = 0

        s_farm = max_farm_spawns

        wheat_after_farm = wheat - s_farm * 10
        remaining_farmers = len(farmers) - 2 * s_farm

        # Maximum possible warrior spawns this step: 2 farmers per spawn, 12 wheat per spawn
        if remaining_farmers >= 2 and wheat_after_farm >= 12:
            max_war_spawns = min(remaining_farmers // 2, wheat_after_farm // 12)
        else:
            max_war_spawns = 0

        s_war = max_war_spawns

        spawn_farmer_count = 2 * s_farm
        spawn_warrior_count = 2 * s_war

        # Assign farmers to appropriate groups
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack with Warriors; keep Farmers in Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")