from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to Cave
        - spawn farmer: for every two farmers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two farmers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers strategy: spawn farmers first, then spawn warriors, rest farm
        F = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many spawns we can support with current wheat and number of Farmers
        spawns_farmers = min(F // 2, wheat // 10)
        n_sf = spawns_farmers * 2  # number of Farmers assigned to "spawn farmer"

        # Wheat left after reserving for farmer spawns
        wheat_after_farm = wheat - spawns_farmers * 10

        # Remaining farmers available to attempt warrior spawns
        remaining_farmers = F - n_sf
        spawns_warriors = min(remaining_farmers // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2  # number of Farmers assigned to "spawn warrior"

        # Assignors
        # First n_sf Farmers to "spawn farmer"
        spawn_farmer_assignees = farmers[:n_sf]
        # Next n_sw Farmers to "spawn warrior"
        spawn_warrior_assignees = farmers[n_sf:n_sf + n_sw]
        # Remaining Farmers to "farm"
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