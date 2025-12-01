from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Strategy: All Warriors should go to the Cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Greedy spawning logic using current wheat and available farmers
        wheat = int(getattr(environment.farm, "wheat", 0))
        remaining = list(farmers)

        # First, spawn as many Warriors as possible:
        # Each Warrior spawn requires 2 farmers and 12 wheat
        max_warrior_spawns = min(len(remaining) // 2, wheat // 12)
        for _ in range(max_warrior_spawns * 2):
            f = remaining.pop(0)
            environment.assign_group(f, "spawn warrior")
        wheat -= max_warrior_spawns * 12

        # Then, spawn as many Farmers as possible with remaining farmers and wheat
        # Each Farmer spawn requires 2 farmers and 10 wheat
        max_farm_spawns = min(len(remaining) // 2, wheat // 10)
        for _ in range(max_farm_spawns * 2):
            f = remaining.pop(0)
            environment.assign_group(f, "spawn farmer")
        wheat -= max_farm_spawns * 10

        # Remaining farmers stay in the village to farm
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: all Warriors attack; Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")