from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Step-based spawn budgeting
        if step < 3:
            max_spawns = 0
        elif step < 6:
            max_spawns = 1
        else:
            max_spawns = 2

        # Compute how many spawns we can support this step
        # Each spawn requires 2 farmers and a Wheat cost (10 for Farmer, 12 for Warrior)
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_farmers = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_farmers // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        # Assign farmers to groups
        spawn_farmer_assignees = farmers[:n_sf]
        spawn_warrior_assignees = farmers[n_sf:n_sf + n_sw]
        farm_assignees = farmers[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are no farmers, Warriors have already been sent to cave above.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should move back to Village to farm or spawn
                environment.assign_group(c, "village")