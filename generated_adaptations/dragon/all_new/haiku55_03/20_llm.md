## Diagnosis

The required failures are still "the Dragon is not dead by step 30," and starvation is not reported. The cycle timing is safe, so the problem is damage throughput. Two things limit it:

1. **The wheat reserve is too large.** Keeping one wheat per villager, including farmers who are not going to eat soon, blocks spawning on many steps. Each warrior we don't spawn is about one fewer attacker, which costs 3 damage per step for the rest of the fight.
2. **Spawn pairs are not consumed.** A pair in the "spawn" group stays a villager, so farmers can be kept in that group every step without losing farming output beyond the step itself. The previous code only spawned when the spare-wheat check passed, so it wasted steps when wheat was enough.

## Revised strategy

**Village**
- **Eat:** warriors at hunger ≥ 1, farmers at ≥ 2, and anyone at ≥ 4 eats first, most hungry first.
- **Reserve, estimated from real demand:** instead of one wheat per villager, reserve one wheat for each villager who will need a meal within the next step. That is villagers in the Village with hunger ≥ 1, plus warriors currently in the Cave, since they will return to eat.
- **Spawn every step while affordable:** pairs of farmers stay in "spawn warrior" each step. Spawns are not limited to one pair per step, so wheat is converted into attackers as fast as possible.
- **Launch every fed, healthy warrior** (hp ≥ 3, hunger ≤ 1) to the Cave.
- **Everyone else farms.**

**Cave**
- Warriors attack while hunger ≤ 2 and hp ≥ 2. At hunger 3 they return to the Village, arriving with hunger 4 at most, so they eat before the 6-step limit.
- Farmers go back to farming.

I could not run the unit tests or the simulator here, so these numbers are untested. If the Dragon still survives step 30, the first values to check are the reserve estimate and whether the spawn pool is too small.

```py
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
```