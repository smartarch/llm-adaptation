## Analysis of the remaining failure

Only one test still fails: `seed=3` reaches step 30 with the Dragon alive. The mechanics, starvation rules, and Cave rules all pass. The issue is damage output, which is limited by how quickly the army grows.

The reserve is the main brake. `ceil(n/6)` wheat is held back every step, and with about 10 villagers that is 2 wheat that never goes into a spawn. Farm income is high enough (about 5 wheat per Farmer per step) that a smaller reserve still covers the meals, since each meal costs only 1 wheat and the hungry villagers are fed first.

The farmer target of 8 also stops Farmer spawns once the farm is large enough, so any later spare wheat goes to Warriors. That is good, but it can be tuned upward a little, since an extra Farmer pays back its cost in about two steps.

## Changes

- **Smaller reserve.** The reserve is `max(1, ceil(n/8))`. Meals are still funded first, so starvation is not affected.
- **Higher farmer target.** The target is raised from 8 to 10. Farmers spawned early pay back their 10-wheat cost in about two steps, which speeds up the Warrior build-up later.

The priority order, the Cave rules, and the explicit assignment of every component are unchanged.

I could not run the test suite here, so this is a tuning change aimed at the failing `seed=3` case. If it still fails, the next place to look is the number of Warrior spawns in the first ten steps.

```py
import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Meals first: warriors eat at >= 2 steps since last meal, farmers at >= 3,
        and anyone at >= 4 is fed first.
      - Spawning is planned before the Cave dispatch. Spawn pairs are drawn from
        fresh (fed, non-hungry) villagers in the Village, preferring farmers so
        that warriors keep attacking when possible.
          * two Warriors early (to attack as soon as possible),
          * two Farmers to grow wheat income,
          * more Farmers while the farmer count is below the target (10),
          * then Warriors with all leftover wheat.
      - The wheat reserve is small (about an eighth of the villagers, at least 1),
        enough to cover the next meals given farm income.
      - Fed warriors that were not used for spawning go to the Cave to attack.
      - In the Cave, a warrior starts heading back at >= 2 steps since its last
        meal (at 2 only if another warrior stays to attack). At >= 3 it always returns.
      - Remaining farmers farm in the Village.
    """

    WARRIOR_EAT_THRESHOLD = 2
    FARMER_EAT_THRESHOLD = 3
    CRITICAL_HUNGER = 4
    CAVE_SOFT_RETURN = 2
    CAVE_FORCED_RETURN = 3
    WARRIOR_COST = 12
    FARMER_COST = 10
    TARGET_FARMERS = 10
    MIN_WARRIOR_SPAWNS = 2
    MIN_FARMER_SPAWNS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def _needs_meal(self, c):
        if c.steps_since_meal >= self.CRITICAL_HUNGER:
            return True
        if c.role == "Warrior":
            return c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
        return c.steps_since_meal >= self.FARMER_EAT_THRESHOLD

    def assign_in_village(self, components, environment, group_ids, step: int):
        if step <= 1:
            self.warriors_spawned = 0
            self.farmers_spawned = 0

        wheat = environment.farm.wheat
        assigned = set()

        # 1) Meals first, most-starved first.
        hungry = sorted(
            [c for c in components if self._needs_meal(c)],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if wheat >= 1:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                wheat -= 1

        # Fresh pools: fed villagers that are not eating and not hungry.
        farmers_pool = [c for c in components
                        if id(c) not in assigned and c.role == "Farmer"
                        and not self._needs_meal(c)]
        warriors_pool = [c for c in components
                         if id(c) not in assigned and c.role == "Warrior"
                         and not self._needs_meal(c)]

        farmers_total = sum(1 for c in components if c.role == "Farmer")

        # 2) Plan spawns. Each spawn needs a pair of villagers in the spawn group.
        reserve = max(1, math.ceil(len(components) / 8))
        spare = wheat - reserve

        def take_pair():
            # Prefer farmers as spawners so that warriors keep attacking.
            pair = []
            while len(pair) < 2 and farmers_pool:
                pair.append(farmers_pool.pop(0))
            while len(pair) < 2 and warriors_pool:
                pair.append(warriors_pool.pop(0))
            return pair if len(pair) == 2 else None

        def spawn(group):
            pair = take_pair()
            if pair is None:
                return False
            for c in pair:
                environment.assign_group(c, group)
                assigned.add(id(c))
            return True

        # a) Early Warriors until the minimum is reached.
        while self.warriors_spawned < self.MIN_WARRIOR_SPAWNS and spare >= self.WARRIOR_COST:
            if not spawn("spawn warrior"):
                break
            self.warriors_spawned += 1
            spare -= self.WARRIOR_COST

        # b) Farmers for wheat income.
        while self.farmers_spawned < self.MIN_FARMER_SPAWNS and spare >= self.FARMER_COST:
            if not spawn("spawn farmer"):
                break
            self.farmers_spawned += 1
            farmers_total += 1
            spare -= self.FARMER_COST

        # c) More Farmers while the farmer count is below the target.
        while farmers_total < self.TARGET_FARMERS and spare >= self.FARMER_COST:
            if not spawn("spawn farmer"):
                break
            self.farmers_spawned += 1
            farmers_total += 1
            spare -= self.FARMER_COST

        # d) Warriors with all leftover wheat.
        while spare >= self.WARRIOR_COST:
            if not spawn("spawn warrior"):
                break
            self.warriors_spawned += 1
            spare -= self.WARRIOR_COST

        # 3) Fed warriors not used for spawning go to the Cave to attack.
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior" and not self._needs_meal(c):
                environment.assign_group(c, "cave")
                assigned.add(id(c))

        # 4) Everyone else (farmers, hungry warriors that could not eat) farms.
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        for c in farmers:
            environment.assign_group(c, "village")

        returning = set()
        # Most hungry first.
        for c in sorted(warriors, key=lambda w: w.steps_since_meal, reverse=True):
            if c.steps_since_meal >= self.CAVE_FORCED_RETURN:
                returning.add(id(c))
            elif c.steps_since_meal >= self.CAVE_SOFT_RETURN:
                attackers_left = len(warriors) - len(returning) - 1
                if attackers_left >= 1:
                    returning.add(id(c))

        for c in warriors:
            if id(c) in returning:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```