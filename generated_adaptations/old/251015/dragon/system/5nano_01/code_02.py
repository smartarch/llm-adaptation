import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Warriors -> cave (to go attack)
        - Farmers -> decide between:
            spawn farmer (2 farmers + 10 wheat per spawn)
            spawn warrior (2 farmers + 12 wheat per spawn)
            remaining farmers -> farm
        """
        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # 1) Send all Warriors to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning based on current wheat
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0)

        total_farmers = len(farmers)

        # Determine how many "spawn farmer" operations we can support now
        spawns_farmers = min(total_farmers // 2, max(0, wheat // 10))
        assigned = 0

        # Assign first 2*spawns_farmers farmers to spawn farmer
        for idx, f in enumerate(farmers):
            if idx < 2 * spawns_farmers:
                environment.assign_group(f, "spawn farmer")
                assigned += 1
            else:
                break

        # Remaining wheat after allocating to spawn farmers
        wheat_after_farm_spawns = wheat - spawns_farmers * 10

        # Farmers left that can participate in spawning warriors
        remaining_farmers_for_warrior_spawns = farmers[2 * spawns_farmers:]

        spawns_warriors = 0
        if wheat_after_farm_spawns > 0:
            spawns_warriors = min(len(remaining_farmers_for_warrior_spawns) // 2,
                                  wheat_after_farm_spawns // 12)

        # Assign to spawn warrior for 2*spawns_warriors farmers
        for i, f in enumerate(remaining_farmers_for_warrior_spawns):
            if i < 2 * spawns_warriors:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # If there are any remaining farmers not yet assigned (in case spawns_farmers was 0),
        # they would be assigned in the loop above as either spawn warriors or farm.
        # This ensures every Farmer is assigned to exactly one group.

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