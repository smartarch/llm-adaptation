## Diagnosis

The remaining failures are all "the Dragon is not dead by step 30". The earlier fixes made the strategy safe from starvation, but the damage output is still too low:

1. **Attack gaps.** Warriors return to the Village too early (at `steps_since_meal >= 3`), then wait for the hunger reset before they go back out. Every gap lets the Dragon regenerate 5 HP. Warriors also need to be sent out again immediately after eating.
2. **Too little damage per step.** Warriors are the only real damage source (3 per attack, versus 1 for farmers), so the army has to grow faster. The previous version kept a reserve and spawned only when it was comfortable, which slowed growth.
3. **Eating and launching happened in separate cycles.** A warrior that eats in the Village at step *t* should be able to leave at *t+1* rather than waiting for the next threshold.

## Revised strategy

**Village**
- **Warriors eat early.** A warrior with `steps_since_meal >= 1` eats, so it is fed on each visit and can return to the Cave at once. Farmers eat at `>= 2`, since they stay in the Village.
- **Starvation override.** Any villager with `steps_since_meal >= 4` eats first, regardless of its role or the order.
- **Launch fed warriors immediately.** A healthy warrior (hp ≥ 3) with `steps_since_meal <= 1` goes to the Cave. Warriors that just ate are back in the fight on the next step.
- **Spawn aggressively.** Pairs of idle farmers become a new warrior whenever the wheat left after this step's meals covers 12 wheat plus one meal per villager. Wheat spent on warriors pays back as damage, and the reserve protects against starvation.
- **Everyone else farms.**

**Cave**
- Warriors attack while `steps_since_meal <= 3` and `hp >= 2`.
- At `steps_since_meal >= 4` or low HP, a warrior returns to the Village.
- Farmers that somehow reach the Cave go straight back to farming.

The cycle is roughly: attack for up to four steps, return and eat, then go back out at once. With a few warriors on staggered cycles, some warrior should attack on almost every step.

The optimal rotation depends on the simulator's exact timing rules, so the thresholds are tuning parameters. I could not run the simulator here, so treat the thresholds as the first things to adjust if the win rate does not improve.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: warriors eat as soon as they are slightly hungry, so they can
        go back to the Cave right away. Farmers eat at 2 steps. Anyone at 4+
        steps eats first. Healthy, freshly fed warriors go to the Cave. Pairs of
        idle farmers spawn new warriors whenever spare wheat covers the cost
        and a one-meal reserve for every villager. Everyone else farms.
      - Cave: warriors attack while fed (steps_since_meal <= 3) and healthy
        (hp >= 2). Otherwise they return to the Village to eat. Farmers never
        fight and go back to farming.
    """

    WARRIOR_EAT_THRESHOLD = 1     # warriors eat on every visit once slightly hungry
    FARMER_EAT_THRESHOLD = 2      # farmers stay home, so they can wait a little longer
    STARVING_THRESHOLD = 4        # always eat at this point, regardless of role
    LAUNCH_FRESH_STEPS = 1        # warriors this fresh are sent to attack
    MIN_WARRIOR_HP_LAUNCH = 3     # warriors below this stay home
    CAVE_ATTACK_MAX_HUNGER = 3    # attack while steps_since_meal <= this
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

        # 3. Spawning: pairs of idle farmers become a new warrior.
        farmers_idle = [c for c in remaining if c.role == "Farmer"]
        if dragon_alive:
            while len(farmers_idle) >= 2 and spare >= self.WARRIOR_COST:
                assign(farmers_idle.pop(0), "spawn warrior")
                assign(farmers_idle.pop(0), "spawn warrior")
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