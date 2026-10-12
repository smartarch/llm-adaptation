from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave (to attack in the next phase)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Wheat available in the Farm (read-only in this step; we use current value)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # 3) Spawn logic: assign some farmers to spawn groups if wheat allows
        idx = 0
        # If at least 2 farmers and >=10 wheat, assign two to spawn farmer
        if len(farmers) - idx >= 2 and wheat >= 10:
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            idx = 2

        # If at least 2 more farmers available and >=12 wheat, assign two to spawn warrior
        if len(farmers) - idx >= 2 and wheat >= 12:
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 4) Remaining farmers stay in farming role
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

        # Note: Any farmers not explicitly assigned by above logic will default to the last assigned group.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: attack with Warriors; move Farmers back to Village
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                # Farmers should stay in the Village
                environment.assign_group(comp, "village")