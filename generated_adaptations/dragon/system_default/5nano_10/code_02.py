from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the cave (to attack the Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Allocate farmers to farming/spawn groups
        # We'll reserve up to 2 farmers for "spawn farmer" and up to 2 for "spawn warrior"
        # Rest go to farming.
        s_f_spawn = min(2, len(farmers) // 2)
        remaining_farmers_after_f_spawn = len(farmers) - s_f_spawn
        s_w_spawn = min(2, remaining_farmers_after_f_spawn // 2)
        s_farm = remaining_farmers_after_f_spawn - s_w_spawn

        idx = 0
        # Assign to "spawn farmer"
        for _ in range(s_f_spawn):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Assign to "spawn warrior"
        for _ in range(s_w_spawn):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers -> "farm"
        for _ in range(s_farm):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # If any farmers remain (edge cases), assign them to farming as a fallback
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")