from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed villagers on time (warriors at 1+ steps, farmers at 2+,
        anyone at 4+ first). Reserve wheat only for meals that are actually
        due soon. Pairs of farmers stay in the spawn group each step while wheat
        allows, so warriors are produced as fast as possible without taking
        fighters out of the fight. Fed, healthy warriors go to the Cave. Everyone
        else farms.
      - Cave: warriors attack while fed (steps_since_meal <= 2) and healthy
        (hp >= 2), then return to the Village to eat. Farmers go back to farm.
    """

    WARRIOR_EAT_THRESHOLD = 1     # warriors eat on each visit once slightly hungry
    FARMER_EAT_THRESHOLD = 2      # farmers stay home, so they can wait a little longer
    STARVING_THRESHOLD = 4        # always eat at this point, regardless of role
    LAUNCH_FRESH_STEPS = 1        # warriors this fresh may be launched
    MIN_WARRIOR_HP_LAUNCH = 3     # warriors below this stay home
    CAVE_ATTACK_MAX_HUNGER = 2    # attack while steps_since_meal <= this
    MIN_WARRIOR_HP_CAVE = 2       # warriors below this retreat from the Cave
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

        # 1. Eating: starving villagers first, then warriors and farmers that
        #    reached their own thresholds. Most hungry first.
        def needs_meal(c):
            if c.steps_since_meal >= self.STARVING_THRESHOLD:
                return True
            if c.role == "Warrior":
                return c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
            return c.steps_since_meal >= self.FARMER_EAT_THRESHOLD

        hungry = sorted(
            [c for c in components if needs_meal(c)],
            key=lambda x: -x.steps_since_meal,
        )
        eat_budget = wheat
        for c in hungry:
            if eat_budget > 0:
                assign(c, "eat")
                eat_budget -= 1
        wheat_after_meals = eat_budget

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Reserve wheat only for meals due soon: villagers in the Village that
        #    are already partly hungry, plus warriors in the Cave who return to eat.
        due_soon_village = sum(1 for c in remaining if c.steps_since_meal >= 1)
        cave_warriors = sum(1 for w in environment.warriors if w.location == "Cave")
        reserve = due_soon_village + cave_warriors + 1
        spare = wheat_after_meals - reserve

        # 3. Spawning: pairs of farmers stay in the spawn group while wheat allows.
        #    Warriors are only used as spawn material if farmers run out.
        if dragon_alive:
            farmers = [c for c in remaining if c.role == "Farmer"]
            others = [c for c in remaining if c.role != "Farmer"]
            pool = farmers + others
            while len(pool) >= 2 and spare >= self.WARRIOR_COST:
                assign(pool.pop(0), "spawn warrior")
                assign(pool.pop(0), "spawn warrior")
                spare -= self.WARRIOR_COST

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Launch: every fed, healthy warrior goes to the Cave.
        if dragon_alive:
            for c in remaining:
                if (c.role == "Warrior"
                        and c.hp >= self.MIN_WARRIOR_HP_LAUNCH
                        and c.steps_since_meal <= self.LAUNCH_FRESH_STEPS):
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
            elif (c.steps_since_meal > self.CAVE_ATTACK_MAX_HUNGER
                  or c.hp < self.MIN_WARRIOR_HP_CAVE):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")