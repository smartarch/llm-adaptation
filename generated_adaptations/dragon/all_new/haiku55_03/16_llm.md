## Diagnosis

The required failures are still "the Dragon is not dead by step 30," and starvation is no longer reported, so the cycle timing is now safe. The problem is damage throughput:

1. **Warriors cycle in and out without a target.** Every healthy warrior launches as soon as it has eaten. The Cave then fills and empties in bursts, and the Dragon regenerates during the gaps.
2. **The Cave can get too crowded.** Dragon retaliation hits everyone in the Cave, so sending every warrior at once wastes HP.
3. **Launch timing ignores the attack window.** A warrior that enters with hunger 1 has three attack steps before it must leave, and the optional test expects two attacks within four steps. Warriors that were sent out just before a meal were often unable to deliver that.

## Revised strategy

**Village**
- Eat rule is unchanged: warriors at `steps_since_meal >= 1`, farmers at `>= 2`, and anyone at `>= 4` first.
- Keep the full reserve of one wheat per villager, so next step's meals are always covered.
- Spawn warriors from pairs of villagers, preferring farmers, whenever spare wheat covers 12.
- **Launch to a target, not to a threshold.** Fed, healthy warriors (hp ≥ 3, hunger ≤ 1) enter the Cave only while the number of warriors already attacking is below `TARGET_CAVE_ATTACKERS`. This keeps the Cave at a steady number of attackers, so each step has damage and the group is not wiped out by retaliation.

**Cave**
- A warrior attacks while `steps_since_meal <= 2` and `hp >= 2`, then returns, so it can eat before the limit.
- Farmers go back to farming at once.

With a target of about three attackers and staggered entry, one attacker is typically leaving while another is entering, so the Dragon sees near-continuous hits.

I cannot run the tests or the simulator here, so the first values to tune if the Dragon is still alive at step 30 are `TARGET_CAVE_ATTACKERS` and `CAVE_ATTACK_MAX_HUNGER`.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed everyone on time (warriors at 1+ steps, farmers at 2+,
        anyone at 4+ first) while keeping one wheat per villager in reserve.
        Spare wheat spawns warriors from pairs of villagers. Fed, healthy
        warriors are launched to the Cave only while the Cave holds fewer than
        TARGET_CAVE_ATTACKERS attackers, so the Dragon is hit almost every step
        without the group being wiped out by retaliation. Everyone else farms.
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
    TARGET_CAVE_ATTACKERS = 3     # keep roughly this many warriors attacking
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

        # 4. Launch: fed, healthy warriors go to the Cave, up to the target count.
        #    Warriors already in the Cave are counted from the environment.
        cave_attackers = sum(
            1 for w in environment.warriors
            if w.location == "Cave" and w.hp >= self.MIN_WARRIOR_HP_CAVE
        )
        if dragon_alive:
            # Prefer the healthiest warriors that are freshly fed.
            candidates = sorted(
                [c for c in remaining
                 if c.role == "Warrior"
                 and c.hp >= self.MIN_WARRIOR_HP_LAUNCH
                 and c.steps_since_meal <= self.LAUNCH_FRESH_STEPS],
                key=lambda c: -c.hp,
            )
            slots = max(0, self.TARGET_CAVE_ATTACKERS - cave_attackers)
            for c in candidates[:slots]:
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