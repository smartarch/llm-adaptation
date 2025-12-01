from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Identify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave for early DPS
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Greedy spawning: prefer Warrior spawns first to boost early DPS
        wheat = getattr(environment.farm, "wheat", 0)
        n_farmers = len(farmers)

        max_war_spawns = 0
        if n_farmers >= 2 and wheat >= 12:
            max_war_spawns = min(n_farmers // 2, wheat // 12)

        remaining_farmers = n_farmers - 2 * max_war_spawns
        wheat_after_war = wheat - 12 * max_war_spawns

        max_farm_spawns = 0
        if remaining_farmers >= 2 and wheat_after_war >= 10:
            max_farm_spawns = min(remaining_farmers // 2, wheat_after_war // 10)

        # 3) Assign groups for Farmers
        idx = 0
        # First the Warrior spawns
        for i in range(max_war_spawns * 2):
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")
            idx += 1
        # Then the Farmer spawns
        for i in range(max_farm_spawns * 2):
            c = farmers[idx]
            environment.assign_group(c, "spawn farmer")
            idx += 1
        # Rest stay farming in Village
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: attack with Warriors; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")