import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Warriors -> cave (to go attack)
        - Farmers -> spawn farmers in small batches if wheat allows, else farm
        - Optionally spawn warriors if enough wheat and farmers are available
        - Remaining farmers -> farm
        """
        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # 1) Send all Warriors to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Wheat info (current wheat in farm)
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0)

        num_farmers = len(farmers)

        # 3) Determine spawn farmer actions (conservative batching)
        spawns_farmers = 0
        if num_farmers >= 4 and wheat >= 20:
            spawns_farmers = 2  # spawn 2 farmers (needs 4 farmers total)
        elif num_farmers >= 2 and wheat >= 10:
            spawns_farmers = 1  # spawn 1 farmer (needs 2 farmers)

        # Assign 2*spawns_farmers farmers to "spawn farmer"
        idx = 0
        for _ in range(spawns_farmers * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        remaining_farmers = farmers[idx:]  # farmers not used for spawn farmers

        # Wheat after farm spawns
        wheat_after_farm_spawns = wheat - spawns_farmers * 10

        # 4) Determine possible spawns for warriors using remaining farmers and wheat
        spawns_warriors = 0
        if len(remaining_farmers) >= 2 and wheat_after_farm_spawns >= 12:
            spawns_warriors = min(len(remaining_farmers) // 2, wheat_after_farm_spawns // 12)

        # Assign 2*spawns_warriors farmers to "spawn warrior"
        for i in range(spawns_warriors * 2):
            if i < len(remaining_farmers):
                environment.assign_group(remaining_farmers[i], "spawn warrior")

        # Remaining farmers after both spawn operations go to farming
        start_idx_for_farm = spawns_farmers * 2 + spawns_warriors * 2
        for j in range(start_idx_for_farm, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # Note: This ensures every Farmer is assigned to exactly one group.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors -> attack (attack the Dragon)
        - Farmers -> village (go back to the Village)
        """
        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")