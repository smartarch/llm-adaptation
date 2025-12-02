import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: Stay in the Village and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, spawn a new Farmer
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, spawn a new Warrior
        """
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # Use farmers to fund spawns
        max_f_spawns = min(len(farmers) // 2, wheat // 10)
        spawn_farmers = farmers[:2 * max_f_spawns]
        remaining_farmers_after_f = farmers[2 * max_f_spawns:]

        max_w_spawns = min(len(remaining_farmers_after_f) // 2, wheat // 12)
        spawn_warriors = remaining_farmers_after_f[:2 * max_w_spawns]
        remaining_farmers_after_w = remaining_farmers_after_f[2 * max_w_spawns:]

        farmers_to_farm = remaining_farmers_after_w

        # Assign groups
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")
            else:
                if c in spawn_farmers:
                    environment.assign_group(c, "spawn farmer")
                elif c in spawn_warriors:
                    environment.assign_group(c, "spawn warrior")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")