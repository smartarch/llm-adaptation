## Fix

The seed=3 failures come from the Village rule that holds back low-HP warriors. A warrior with `hp <= 2` was assigned to "farm" instead of "cave", which violates "should go to the Cave." The Cave rule also recalled warriors with `hp <= 2` before they could attack, which violates "should attack after moving to the Cave." The two rules together made the low-HP warriors fail both requirements.

**Changes**
- **Village:** Every fed warrior (`steps_since_meal < 3`) goes to the Cave, regardless of HP. Only warriors that need a meal are assigned to "eat" instead.
- **Cave:** A warrior attacks whenever it is still fed (`steps_since_meal <= 3`), regardless of HP. This means every warrior that arrives in the Cave attacks on that step. Warriors that are hungry return to the Village.
- Farmers, spawning, and the one-group-per-villager rule are unchanged.

**Trade-off:** A warrior that must eat in the Village cannot also go to the Cave on that step. Meals are kept at the minimum needed (only at `steps_since_meal >= 3`), so these conflicts are as rare as the starvation rule allows. A warrior that is still fed is never kept out of the Cave for HP reasons. Warriors cannot starve, because the Village eat rule and the Cave return rule both trigger before the 6-step limit.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge strategy (revised again):
      - Every fed warrior goes to the Cave, regardless of HP, so none is
        held back on the farm.
      - Warriors attack in the Cave while they are still fed, so every
        warrior that arrives attacks on arrival.
      - Warriors eat only when they actually need it, and then return.
      - Farmers stay in the Village, eat when needed and farm wheat.
      - One farmer is spawned early; surplus wheat then goes to warrior spawns.
    """

    WARRIOR_EAT_AFTER = 3     # warriors eat in the Village once they are close to starving
    FARMER_EAT_AFTER = 4      # farmers eat before reaching the 6-step starvation limit
    CAVE_MAX_STEPS = 3        # warriors in the Cave attack only while steps_since_meal <= this
    WHEAT_RESERVE = 2
    WARRIOR_COST = 12
    FARMER_COST = 10
    SPAWN_CUTOFF_STEP = 22    # stop spawning late in the fight

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawned = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat_group = []
        warriors = []
        farmers = []

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.WARRIOR_EAT_AFTER:
                    eat_group.append(c)
                else:
                    warriors.append(c)
            else:
                if c.steps_since_meal >= self.FARMER_EAT_AFTER:
                    eat_group.append(c)
                else:
                    farmers.append(c)

        # Each meal costs 1 wheat.
        spendable = wheat - len(eat_group) - self.WHEAT_RESERVE

        for c in eat_group:
            environment.assign_group(c, "eat")

        # Spawning uses non-eating farmers.
        spawn_pool = list(farmers)
        spawned = set()

        if step < self.SPAWN_CUTOFF_STEP:
            # Guarantee at least one farmer spawn when affordable.
            if not self._farmer_spawned and len(spawn_pool) >= 2 \
                    and spendable >= self.FARMER_COST:
                pair = spawn_pool[:2]
                spawn_pool = spawn_pool[2:]
                for c in pair:
                    environment.assign_group(c, "spawn farmer")
                    spawned.add(id(c))
                spendable -= self.FARMER_COST
                self._farmer_spawned = True

            # Warriors are the main damage source; spawn them whenever affordable.
            while len(spawn_pool) >= 2 and spendable >= self.WARRIOR_COST:
                pair = spawn_pool[:2]
                spawn_pool = spawn_pool[2:]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawned.add(id(c))
                spendable -= self.WARRIOR_COST

        # Every non-eating warrior goes to the Cave.
        for c in warriors:
            environment.assign_group(c, "cave")

        # Remaining farmers keep farming.
        for c in spawn_pool:
            if id(c) not in spawned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal <= self.CAVE_MAX_STEPS:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```