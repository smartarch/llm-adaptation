from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _is_warrior(self, c):
        role = getattr(c, "role", "")
        return isinstance(role, str) and role.lower() == "warrior"

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Robust village assignment with step-based spawning:
        - Warriors -> cave (to move to the Cave and attack)
        - Non-Warriors (Farmers or others) -> farm by default
        - A small, capped amount of spawning to create new Farmers/Warriors when wheat allows
        """
        # Classify villagers
        farmers = [c for c in components if not self._is_warrior(c)]
        warriors = [c for c in components if self._is_warrior(c)]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # Step-based spawning caps to accelerate early DPS but stay safe later
        if step <= 2:
            cap_f_spawns = 6
            cap_w_spawns = 6
        elif step <= 5:
            cap_f_spawns = 5
            cap_w_spawns = 4
        elif step <= 8:
            cap_f_spawns = 4
            cap_w_spawns = 3
        else:
            cap_f_spawns = 3
            cap_w_spawns = 2

        # Spawn farmer plan
        max_f_spawns = min(len(farmers) // 2, wheat // 10, cap_f_spawns) if wheat >= 10 else 0
        spawn_farmers = farmers[:2 * max_f_spawns]
        remaining_after_f = farmers[2 * max_f_spawns:]

        # Wheat left after spawning farmers
        wheat_after_f = wheat - 10 * max_f_spawns

        # Spawn warrior plan
        max_w_spawns = 0
        if remaining_after_f and wheat_after_f >= 12:
            max_w_spawns = min(len(remaining_after_f) // 2, wheat_after_f // 12, cap_w_spawns)

        spawn_warriors = remaining_after_f[:2 * max_w_spawns]
        remaining_after_w = remaining_after_f[2 * max_w_spawns:]

        # Identity-based lookup for spawn groups
        spawn_farm_ids = {id(c) for c in spawn_farmers}
        spawn_war_ids = {id(c) for c in spawn_warriors}

        assigned = set()

        # Assign groups
        for c in components:
            if self._is_warrior(c):
                environment.assign_group(c, "cave")
            else:
                cid = id(c)
                if cid in spawn_farm_ids:
                    environment.assign_group(c, "spawn farmer")
                elif cid in spawn_war_ids:
                    environment.assign_group(c, "spawn warrior")
                else:
                    environment.assign_group(c, "farm")
            assigned.add(c)

        # Safety net: ensure everyone is assigned
        for c in components:
            if c not in assigned:
                if self._is_warrior(c):
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Robust cave assignment:
        - Warriors -> attack
        - Non-Warriors -> village
        """
        assigned = set()
        for c in components:
            if self._is_warrior(c):
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
            assigned.add(c)

        # Safety net: ensure everyone is assigned
        for c in components:
            if c not in assigned:
                if self._is_warrior(c):
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")