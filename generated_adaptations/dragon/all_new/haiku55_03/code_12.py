from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: warriors eat once slightly hungry, so they can return to the
        Cave right away. Farmers eat at 2 steps. Anyone at 4+ steps eats first.
        Healthy, freshly fed warriors go to the Cave. Pairs of villagers
        (preferring farmers) spawn new warriors whenever spare wheat covers the
        cost. A half-size meal reserve protects against starvation.
      - Cave: warriors attack while fed (steps_since_meal <= 4) and healthy
        (hp >= 2), so the Dragon rarely gets a step to regenerate. Otherwise
        they return to the Village to eat. Farmers go back to farming.
    """

    WARRIOR_EAT_THRESHOLD = 1     # warriors eat on every visit once slightly hungry
    FARMER_EAT_THRESHOLD = 2      # farmers stay home, so they can wait a little longer
    STARVING_THRESHOLD = 4        # always eat at this point, regardless of role
    LAUNCH_FRESH_STEPS = 1        # warriors this fresh are sent to attack
    MIN_WARRIOR_HP_LAUNCH = 3     # warriors below this stay home
    CAVE_ATTACK_MAX_HUNGER = 4    # attack while steps_since_meal <= this
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

        # 2. Reserve about half a meal per villager for upcoming meals.
        spare = wheat_after_meals - len(components) // 2

        # 3. Spawning: pairs of idle villagers, preferring farmers, become a new warrior.
        if dragon_alive:
            pool = sorted(remaining, key=lambda c: 0 if c.role == "Farmer" else 1)
            while len(pool) >= 2 and spare >= self.WARRIOR_COST:
                assign(pool.pop(0), "spawn warrior")
                assign(pool.pop(0), "spawn warrior")
                spare -= self.WARRIOR_COST

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Launch: healthy, freshly fed warriors go to the Cave.
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