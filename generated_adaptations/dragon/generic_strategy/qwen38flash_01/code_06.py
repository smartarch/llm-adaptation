from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors head to the cave immediately to start dealing damage.
        for w in warriors:
            environment.assign_group(w, "cave")

        available = list(farmers)

        # Convert pairs of farmers into warriors while keeping at least one
        # farmer producing wheat (need >= 3 farmers to spare 2 as parents).
        while len(available) >= 3 and wheat >= 12:
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            wheat -= 12

        # All-in finishing move: if exactly 2 farmers remain and we can afford
        # it, turn them into a warrior. Net damage change is +3-2 = +1 per turn
        # (warriors hit for 3, the two farmers would only hit for 2 combined),
        # and we no longer need wheat production.
        if len(available) == 2 and wheat >= 12:
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            wheat -= 12

        # Everything left over farms to build wheat for future spawns.
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors stay and attack the dragon every step.
                environment.assign_group(c, "attack")
            else:
                # A farmer in the cave is wasting wheat production; send it home.
                environment.assign_group(c, "village")