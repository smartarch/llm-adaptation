from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _is_warrior(self, c):
        role = getattr(c, "role", "")
        return isinstance(role, str) and role.lower() == "warrior"

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Robust village assignment with small, controlled spawning:
        - Warriors -> cave (to move to the Cave and attack)
        - Non-Warriors (Farmers or others) -> farm by default
        - A small, capped amount of spawning to create new Farmers/Warriors when wheat allows
        """
        # Classify villagers
        farmers = [c for c in components if not self._is_warrior(c)]
        warriors = [c for c in components if self._is_warrior(c)]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # Plan spawning (cap to keep risk low)
        max_f_spawns = min(len(farmers) // 2, wheat // 10) if wheat >= 10 else 0
        max_f_spawns = min(max_f_spawns, 2)  # cap to avoid over-spawning

        spawn_farmers = farmers[:2 * max_f_spawns]
        remaining_after_f = farmers[2 * max_f_spawns:]

        max_w_spawns = min(len(remaining_after_f) // 2, (wheat - 10 * max_f_spawns) // 12) if wheat >= 12 else 0
        max_w_spawns = min(max_w_spawns, 2)  # cap to avoid over-spawning

        spawn_warriors = remaining_after_f[:2 * max_w_spawns]
        remaining_after_w = remaining_after_f[2 * max_w_spawns:]

        # Id-based membership to avoid identity issues
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