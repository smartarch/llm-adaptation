from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Greedy adaptation:
      - Keep every villager fed (eat when steps_since_meal >= 3, a safety margin
        below the 6-step starvation limit).
      - Early on, spawn extra warriors (the strongest attackers) when wheat allows.
      - Send warriors to the cave; farmers keep farming for food unless wheat is plentiful.
      - In the cave, attack every step (so the Dragon never regenerates) and retreat
        villagers that are close to starving.
    """

    EAT_THRESHOLD_VILLAGE = 3
    EAT_THRESHOLD_CAVE = 3
    SPAWN_STEP_LIMIT = 10
    WARRIOR_SPAWN_COST = 12
    WHEAT_SURPLUS = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        remaining = []

        # 1) Feed anyone approaching the starvation limit.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE and wheat >= 1:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                remaining.append(c)

        # 2) Spawn a warrior early in the fight if affordable (uses two farmers as inputs).
        farmers_free = [c for c in remaining if c.role == "Farmer"]
        spawned_inputs = set()
        if (step <= self.SPAWN_STEP_LIMIT
                and wheat >= self.WARRIOR_SPAWN_COST
                and len(farmers_free) >= 2):
            for c in farmers_free[:2]:
                environment.assign_group(c, "spawn warrior")
                spawned_inputs.add(id(c))
            wheat -= self.WARRIOR_SPAWN_COST

        # 3) Route the rest.
        for c in remaining:
            if id(c) in spawned_inputs:
                continue
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:  # Farmer
                if wheat >= self.WHEAT_SURPLUS:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_CAVE:
                # Retreat to eat before starvation sets in.
                environment.assign_group(c, "village")
            else:
                # Keep attacking every step so the Dragon never regenerates.
                environment.assign_group(c, "attack")