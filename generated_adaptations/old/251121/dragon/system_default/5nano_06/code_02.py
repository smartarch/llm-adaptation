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

        # 1) Send all Warriors to the Cave (path to cave)
        for w in warriors:
            environment.assign_group(w, "cave")  # they will move to the cave

        # 2) Farmers management in Village
        # Default: assign all farmers to farming
        for f in farmers:
            environment.assign_group(f, "farm")

        total_farmers = len(farmers)
        current_wheat = getattr(environment.farm, "wheat", 0)

        # 3) Determine spawning allocations based on current wheat and number of farmers
        # s_f: number of pairs allocated to spawn farmer
        s_f = min(total_farmers // 2, current_wheat // 10) if current_wheat >= 10 else 0
        # s_w: number of pairs allocated to spawn warrior after reserving s_f pairs
        s_w = 0
        if total_farmers > 2 * s_f:
            remaining_after_f_farms = total_farmers - 2 * s_f
            s_w = min(remaining_after_f_farms // 2, current_wheat // 12) if current_wheat >= 12 else 0

        # Reassignment based on s_f and s_w
        # Start by collecting farmers in a deterministic order
        # We'll reassign the first 2*s_f to spawn farmer, next 2*s_w to spawn warrior, rest stay farming
        idx = 0
        # Reassign to spawn farmer
        for _ in range(2 * s_f):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Reassign to spawn warrior
        for _ in range(2 * s_w):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # The remaining farmers stay in farm (already assigned earlier)
        # If some farmers were not touched (due to small numbers), they remain in "farm"


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