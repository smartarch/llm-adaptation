## Strategy: Warrior Surge with Scheduled Meals

The strategy has three goals: deal damage quickly with warriors, keep every villager fed within the 6-step starvation limit, and convert surplus wheat into extra warriors early so the damage output grows.

**Village phase (`assign_in_village`)**
- **Meals first:** Any villager with `steps_since_meal >= 3` goes to "eat". The threshold leaves a margin below the 6-step starvation limit, because a warrior needs one step to return from the Cave.
- **Warriors:** Warriors that are fed (`steps_since_meal < 3`) and healthy go to the "cave" to attack.
- **Farmers:** Fed farmers stay on "farm" to produce wheat.
- **Spawning:** Warriors are the priority. Two non-eating farmers go to "spawn warrior" whenever wheat covers the 12-wheat cost plus a reserve of 4 wheat for upcoming meals. Farmers are spawned only when wheat is plentiful (at least 30 wheat plus the reserve), and only in the early part of the fight. Spawning draws only from farmers, so warriors are never diverted from the attack.
- Each eligible spawn pair is removed from the farm pool, so that a villager is never in two groups.

**Cave phase (`assign_in_cave`)**
- Warriors attack while they are healthy (`hp > 2`) and fed (`steps_since_meal < 3`).
- Warriors that are hungry or badly wounded return to the "village" to eat or recover.
- Farmers never fight. They go back to the Village, as the task requires.

**Safety notes**
- Wheat reserve prevents spending down to zero, so meals can always be paid for.
- The heuristic thresholds (3 steps for meals, 2 HP for retreat) are chosen so that no villager reaches the starvation limit while away from food.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge strategy:
      - Warriors fight in the Cave while fed and healthy.
      - Farmers stay in the Village, eat on schedule and farm wheat.
      - Surplus wheat is converted into new Warriors early on.
      - Meals are scheduled before starvation (6 steps) can occur.
    """

    MEAL_THRESHOLD = 3        # eat when this many steps without a meal
    RETREAT_HP = 2            # warriors at or below this HP retreat from the Cave
    WHEAT_RESERVE = 4         # wheat kept aside for future meals
    WARRIOR_COST = 12
    FARMER_COST = 10
    FARMER_SPAWN_WHEAT = 30   # only spawn farmers when wheat is abundant
    SPAWN_CUTOFF_STEP = 20    # stop spawning late in the fight

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        spendable = wheat - self.WHEAT_RESERVE

        needs_meal = []
        fed_warriors = []
        fed_farmers = []

        for c in components:
            if c.steps_since_meal >= self.MEAL_THRESHOLD:
                needs_meal.append(c)
            elif c.role == "Warrior":
                fed_warriors.append(c)
            else:
                fed_farmers.append(c)

        # Eat first; eating consumes 1 wheat each, so account for it.
        for c in needs_meal:
            environment.assign_group(c, "eat")
            spendable -= 1

        # Spawning: pick from fed farmers only (warriors should attack).
        spawn_pool = list(fed_farmers)
        spawned_ids = set()

        if step < self.SPAWN_CUTOFF_STEP:
            # Prefer spawning warriors.
            while len(spawn_pool) >= 2 and spendable >= self.WARRIOR_COST:
                pair = spawn_pool[:2]
                spawn_pool = spawn_pool[2:]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawned_ids.add(id(c))
                spendable -= self.WARRIOR_COST

            # Spawn farmers only when wheat is clearly abundant.
            while (len(spawn_pool) >= 2
                   and spendable >= self.FARMER_SPAWN_WHEAT
                   and spendable >= self.FARMER_COST):
                pair = spawn_pool[:2]
                spawn_pool = spawn_pool[2:]
                for c in pair:
                    environment.assign_group(c, "spawn farmer")
                    spawned_ids.add(id(c))
                spendable -= self.FARMER_COST

        # Remaining fed villagers: warriors go to the cave, farmers farm.
        for c in fed_warriors:
            if id(c) in spawned_ids:
                continue
            if c.hp <= self.RETREAT_HP:
                environment.assign_group(c, "farm")
            else:
                environment.assign_group(c, "cave")

        for c in spawn_pool:
            environment.assign_group(c, "farm")

        # Any villager that was in fed_farmers but not yet handled.
        for c in fed_farmers:
            if id(c) not in spawned_ids and c not in spawn_pool:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > self.RETREAT_HP \
                    and c.steps_since_meal < self.MEAL_THRESHOLD:
                environment.assign_group(c, "attack")
            elif c.role == "Warrior":
                # Hungry or wounded warriors go back to eat / recover.
                environment.assign_group(c, "village")
            else:
                # Farmers do not fight; send them home.
                environment.assign_group(c, "village")
```