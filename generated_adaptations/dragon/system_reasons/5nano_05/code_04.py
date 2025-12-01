import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all current Warriors to the Cave (they will be attacking once in cave)
        for w in warriors:
            if "cave" in group_ids:
                environment.assign_group(w, "cave")

        # 2) Greedily spawn new Villagers using wheat
        # Use a local wheat counter to maximize spawns in this step
        wheat = getattr(environment.farm, "wheat", 0)

        # List of farmers still in village (unassigned)
        unassigned = list(farmers)

        # First, spawn as many Warriors as possible:
        # Each Warrior spawn consumes 2 farmers + 12 wheat
        idx = 0
        max_warriors = min(len(unassigned) // 2, wheat // 12) if len(unassigned) >= 2 else 0
        for _ in range(max_warriors * 2):
            if idx < len(unassigned) and "spawn warrior" in group_ids:
                environment.assign_group(unassigned[idx], "spawn warrior")
            idx += 1
        wheat -= max_warriors * 12

        # Then, spawn as many Farmers as possible with remaining wheat:
        remaining_farmers = unassigned[idx:]
        max_farmers = min(len(remaining_farmers) // 2, wheat // 10) if len(remaining_farmers) >= 2 else 0
        for _ in range(max_farmers * 2):
            fid = idx
            if fid < len(unassigned) and "spawn farmer" in group_ids:
                environment.assign_group(unassigned[fid], "spawn farmer")
            idx += 1
        wheat -= max_farmers * 10

        # 3) Remaining farmers (if any) go to farming in the Village
        for j in range(idx, len(unassigned)):
            if "farm" in group_ids:
                environment.assign_group(unassigned[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors attack Dragon, Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                if "attack" in group_ids:
                    environment.assign_group(c, "attack")
                elif "cave" in group_ids:
                    environment.assign_group(c, "cave")
            else:
                if "village" in group_ids:
                    environment.assign_group(c, "village")