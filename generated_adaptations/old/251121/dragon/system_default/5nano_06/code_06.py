from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers in this group and 10 wheat, spawn a Farmer
        - spawn warrior: For every two villagers in this group and 12 wheat, spawn a Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Warriors must go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Prepare spawning allocations for farmers (deterministic single-pass)
        total_farmers = len(farmers)
        current_wheat = getattr(environment.farm, "wheat", 0)

        s_f = 0
        if current_wheat >= 10:
            s_f = min(total_farmers // 2, current_wheat // 10)

        remaining = total_farmers - 2 * s_f
        s_w = 0
        if current_wheat >= 12:
            s_w = min(remaining // 2, current_wheat // 12)

        # 3) Build a single mapping so every farmer is assigned exactly once
        mapping = {}
        idx = 0
        # First 2*s_f -> spawn farmer
        for _ in range(2 * s_f):
            if idx < total_farmers:
                mapping[farmers[idx]] = "spawn farmer"
                idx += 1
        # Next 2*s_w -> spawn warrior
        for _ in range(2 * s_w):
            if idx < total_farmers:
                mapping[farmers[idx]] = "spawn warrior"
                idx += 1
        # Remaining -> farm
        for i in range(idx, total_farmers):
            mapping[farmers[i]] = "farm"

        # 4) Apply assignments for all farmers (and default if any misses)
        for f in farmers:
            grp = mapping.get(f, "farm")
            environment.assign_group(f, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (Warriors should go here)
        - cave: Stay in the Cave (not used by our strategy)
        - village: Go to the Village (Farmers return to farming/spawning)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers in the Cave should go back to the Village
                environment.assign_group(c, "village")