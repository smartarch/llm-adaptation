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

        # 2) Wheat budget (local) from the Farm (read-only in environment, but we track ourselves)
        wheat_available = 0
        try:
            wheat_available = environment.farm.wheat
        except Exception:
            wheat_available = 0

        # 3) Spawn logic with incremental wheat deduction
        next_idx = 0  # index of the next unassigned farmer
        # Try to spawn up to two Farmers (cost 10 wheat total)
        if len(farmers) - next_idx >= 2 and wheat_available >= 10:
            environment.assign_group(farmers[next_idx], "spawn farmer")
            environment.assign_group(farmers[next_idx + 1], "spawn farmer")
            next_idx += 2
            wheat_available -= 10

        # Try to spawn up to two Warriors (cost 12 wheat total) using next unassigned farmers
        if len(farmers) - next_idx >= 2 and wheat_available >= 12:
            environment.assign_group(farmers[next_idx], "spawn warrior")
            environment.assign_group(farmers[next_idx + 1], "spawn warrior")
            next_idx += 2
            wheat_available -= 12

        # 4) Remaining farmers stay in farming role
        for i in range(next_idx, len(farmers)):
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