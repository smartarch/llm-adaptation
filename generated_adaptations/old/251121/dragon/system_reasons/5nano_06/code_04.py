from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors must go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available in Farm (read-only in this interface)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 2) Spawn logic (aggressive but gated by wheat and population)
        idx = 0  # index into farmers list for assigning to spawn groups

        # Step-based gating: try to spawn a Warrior early if possible
        # Condition: at least 4 farmers and enough wheat (>=12)
        if len(farmers) - idx >= 4 and wheat >= 12:
            for _ in range(2):  # assign two farmers to spawn warrior
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Spawn farmers if we have enough farmers left and enough wheat
        # Condition: at least 4 remaining farmers and wheat >= 20
        if len(farmers) - idx >= 4 and wheat >= 20:
            for _ in range(4):  # assign four farmers to spawn farmer (produces up to 2 new farmers)
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers stay in the village and farm
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # All farmers not explicitly reassigned remain in farm by default
        # (explicit assignments above ensure correct grouping)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: all Warriors attack the Dragon; Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")