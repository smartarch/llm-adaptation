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
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # Spawn planning based on current wheat
        max_f_spawns = min(len(farmers) // 2, wheat // 10) if wheat >= 10 else 0
        spawn_farmers = farmers[:2 * max_f_spawns]
        remaining_f_after_f = farmers[2 * max_f_spawns:]

        max_w_spawns = min(len(remaining_f_after_f) // 2, wheat // 12) if wheat >= 12 else 0
        spawn_warriors = remaining_f_after_f[:2 * max_w_spawns]
        remaining_f_after_w = remaining_f_after_f[2 * max_w_spawns:]

        # Farmers not used for spawns go to farming
        # (farmers_to_farm = remaining_f_after_w, but we don't need to track separately here)

        assigned = set()

        # Assign all components
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
            assigned.add(c)

        # Safety net: ensure every component is assigned
        for c in components:
            if c not in assigned:
                role = getattr(c, "role", None)
                if role == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        assigned = set()
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
            assigned.add(c)

        # Safety net: ensure every component is assigned
        for c in components:
            if c not in assigned:
                role = getattr(c, "role", None)
                if role == "Warrior":
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")