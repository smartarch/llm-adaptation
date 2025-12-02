from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Move all existing warriors to the cave (to travel to Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Early steps: focus on farming to accumulate wheat
        if step <= 3 or len(farmers) == 0:
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Strategy: spawn Warriors first (if possible), then spawn Farmers
        leftover_farmers = len(farmers)
        leftover_wheat = wheat
        w_spawns = 0
        f_spawns = 0

        # Spawn as many Warriors as possible: needs 2 farmers and 12 wheat per spawn
        while leftover_farmers >= 2 and leftover_wheat >= 12:
            w_spawns += 1
            leftover_farmers -= 2
            leftover_wheat -= 12

        # Then spawn as many Farmers as possible with remaining resources
        while leftover_farmers >= 2 and leftover_wheat >= 10:
            f_spawns += 1
            leftover_farmers -= 2
            leftover_wheat -= 10

        # Assign each farmer to exactly one group in a single pass
        # First 2*w_spawns farmers -> "spawn warrior"
        # Next 2*f_spawns farmers -> "spawn farmer"
        # Remaining farmers -> "farm"
        for idx, f in enumerate(farmers):
            if idx < 2 * w_spawns:
                environment.assign_group(f, "spawn warrior")
            elif idx < 2 * w_spawns + 2 * f_spawns:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack with warriors; farmers go back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")