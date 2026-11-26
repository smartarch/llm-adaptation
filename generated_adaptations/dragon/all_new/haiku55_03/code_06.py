from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed villagers with steps_since_meal >= 2 while keeping one
        wheat per villager in reserve for the meals due next step. Spare wheat
        spawns new warriors from pairs of idle farmers. Fresh, healthy warriors
        are sent to the Cave immediately. Everyone else farms.
      - Cave: warriors attack every step while fed and healthy, so the Dragon
        is hit almost continuously and never gets to regenerate. Hungry or
        badly wounded warriors return to the Village. Farmers never fight.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat early, well before the 6-step limit
    RETREAT_THRESHOLD = 4       # leave the Cave when hunger reaches this
    MIN_WARRIOR_HP_LAUNCH = 3   # warriors below this stay home
    MIN_WARRIOR_HP_CAVE = 2     # warriors below this retreat from the Cave
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign(c, group):
            environment.assign_group(c, group)
            assigned.add(id(c))

        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        # 1. Eating: feed hungry villagers, most hungry first.
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE],
            key=lambda x: -x.steps_since_meal,
        )
        eat_budget = wheat
        for c in hungry:
            if eat_budget > 0:
                assign(c, "eat")
                eat_budget -= 1
        wheat_after_meals = eat_budget

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Reserve: one wheat per villager for the meals due next step.
        reserve = len(components)
        spare = wheat_after_meals - reserve

        # 3. Spawning: pairs of idle farmers become a new warrior when the
        #    surplus covers the cost.
        farmers_idle = [c for c in remaining if c.role == "Farmer"]
        if dragon_alive:
            while len(farmers_idle) >= 2 and spare >= self.WARRIOR_COST:
                assign(farmers_idle.pop(0), "spawn warrior")
                assign(farmers_idle.pop(0), "spawn warrior")
                spare -= self.WARRIOR_COST

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Launch: every fresh, healthy warrior goes to the Cave.
        if dragon_alive:
            for c in remaining:
                if (c.role == "Warrior"
                        and c.hp >= self.MIN_WARRIOR_HP_LAUNCH
                        and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE):
                    assign(c, "cave")

        remaining = [c for c in components if id(c) not in assigned]

        # 5. Everyone else farms.
        for c in remaining:
            assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0
        for c in components:
            if c.role == "Farmer":
                # Farmers do not fight; send them back to farm.
                environment.assign_group(c, "village")
            elif not dragon_alive:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal >= self.RETREAT_THRESHOLD or c.hp < self.MIN_WARRIOR_HP_CAVE:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")