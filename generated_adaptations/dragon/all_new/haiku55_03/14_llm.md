## Diagnosis

The last change raised the Cave hunger limit to 4, so warriors stayed in the Cave too long. The tests flag any warrior that is still in the Cave after 4 steps without eating, because the trip back takes one step and the 6-step starvation limit then gets missed. That is the cause of the new required-test failures.

The Dragon-kill failures remain because the previous cycle was too slow. The fix is to make warriors leave the Cave at the right time and keep them on staggered cycles, so some warrior is always attacking.

## Revised strategy

**Village**
- Warriors eat once `steps_since_meal >= 1`, and farmers at `>= 2`. Anyone at `>= 4` eats first, most hungry first.
- A healthy warrior (hp ≥ 3) with `steps_since_meal <= 1` is sent to the Cave. It is fed on its visit, so it can leave again right away.
- The meal reserve goes back to one wheat per villager, so the meals due next step are always covered.
- Spawning uses pairs of villagers, preferring farmers, whenever spare wheat covers 12 wheat.

**Cave**
- A warrior attacks while `steps_since_meal <= 2` and `hp >= 2`.
- At `steps_since_meal >= 3` it returns to the Village. The trip takes one step, so it arrives with the counter at 4 at most and can eat before the 6-step limit.
- Farmers go back to farming.

Warriors attack for about three steps, return to eat, and go back out immediately. Several warriors on staggered cycles keep attacks on most steps, so the Dragon regenerates less. Some wheat is spent on the reserve, so spawning is slower, but starvation is the first constraint.

I could not run the tests or the simulator here. If the Dragon-kill tests still fail, the first thing to tune is `CAVE_ATTACK_MAX_HUNGER`, and then the spawn reserve.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: warriors eat once slightly hungry so they can return to the
        Cave immediately. Farmers eat at 2 steps. Anyone at 4+ steps eats first.
        Healthy, freshly fed warriors go to the Cave. Pairs of villagers
        (preferring farmers) spawn new warriors when spare wheat covers the
        cost, after keeping one wheat per villager for next step's meals.
      - Cave: warriors attack while fed (steps_since_meal <= 2) and healthy
        (hp >= 2). At 3 steps they return to the Village, so they always eat
        before the 6-step limit. Farmers go back to farming.
    """

    WARRIOR_EAT_THRESHOLD = 1     # warriors eat on every visit once slightly hungry
    FARMER_EAT_THRESHOLD = 2      # farmers stay home, so they can wait a little longer
    STARVING_THRESHOLD = 4        # always eat at this point, regardless of role
    LAUNCH_FRESH_STEPS = 1        # warriors this fresh are sent to attack
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

        # 2. Reserve one wheat per villager for next step's meals.
        spare = wheat_after_meals - len(components)

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
```