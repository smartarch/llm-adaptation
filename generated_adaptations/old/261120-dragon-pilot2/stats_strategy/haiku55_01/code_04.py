from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Villagers in the Village eat before anything else (wheat reserved for meals).
    - Idle farmers are paired into "spawn warrior" groups whenever wheat allows,
      so the number of attackers grows as fast as possible.
    - Warriors attack in the Cave; they rotate out to eat before starving, which
      staggers them so that the Dragon is attacked almost every step (no regeneration).
    - Farmers never enter the Cave; they farm wheat.
    """

    WARRIOR_EAT_AT = 2      # warriors in the Village eat once this many steps have passed
    FARMER_EAT_AT = 3       # farmers in the Village eat at this threshold
    CAVE_LEAVE_AT = 4       # warriors in the Cave go back to eat at this threshold
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Meals first: reserve wheat for villagers that need food.
        eaters = []
        rest = []
        for c in components:
            threshold = self.WARRIOR_EAT_AT if c.role == "Warrior" else self.FARMER_EAT_AT
            if c.steps_since_meal >= threshold:
                eaters.append(c)
            else:
                rest.append(c)

        for c in eaters:
            environment.assign_group(c, "eat")
        wheat -= len(eaters)

        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]

        # 2) Spawn warriors with pairs of idle farmers while wheat allows.
        spawn_ids = set()
        if wheat >= self.WARRIOR_COST and len(farmers) >= 2:
            for c in farmers[:2]:
                environment.assign_group(c, "spawn warrior")
                spawn_ids.add(id(c))
            wheat -= self.WARRIOR_COST

        # 3) Warriors not eating return to the Cave to fight.
        for c in warriors:
            environment.assign_group(c, "cave")

        # 4) Remaining farmers keep farming wheat.
        for c in farmers:
            if id(c) not in spawn_ids:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.CAVE_LEAVE_AT:
                # Keep attacking while fed; this keeps the Dragon from regenerating.
                environment.assign_group(c, "attack")
            else:
                # Hungry warriors and any farmers go back to the Village.
                environment.assign_group(c, "village")