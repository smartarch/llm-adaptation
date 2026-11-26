## Fixing the failures

The test failures come from wheat accounting. The old code sent every hungry villager to "eat" without checking the wheat stock, so with 15 wheat the eat orders could exceed what was available. The strategy also did not reserve wheat for meals due in the next step, so the stock could run out and villagers starved.

The revised strategy:

1. **Budgeted eating:** Villagers who need food (`steps_since_meal >= 3`) are sorted by hunger, most hungry first. Only as many as the current wheat can cover are sent to "eat". Any villager left unfed stays on the farm, which keeps the assignment within the wheat available.
2. **Eat threshold lowered to 3 steps:** Warriors leave the Village with a hunger count of at most 1, attack for up to 3 steps, and return with a hunger count of 3, so they eat on arrival. Every villager eats within a 4-step cycle, well inside the 6-step starvation limit.
3. **Reserve-aware spawning:** A warrior is spawned only when the wheat left after this step's meals covers the 12-wheat cost plus a 2-wheat reserve for next step's meals. Spawning is limited to the early game, because a late warrior cannot deal much damage before the 30-step limit.
4. **Dispatch:** Healthy warriors with a hunger count of at most 2 go to the Cave. Farmers stay on the farm to produce the wheat that pays for food and spawning.
5. **Cave logic:** Warriors attack while they are fed and healthy. They retreat when hungry (`steps_since_meal >= 3`) or at 1 HP. Any farmer in the Cave attacks only while healthy and not hungry.
6. **Complete assignment:** Every component is assigned to exactly one group in each method, using a single pass.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: villagers this hungry are sent to eat (most hungry get priority)
    EAT_THRESHOLD = 3
    # Cave: villagers this hungry return to the village to eat
    CAVE_RETURN_THRESHOLD = 3
    # Warriors may be sent to the cave if their hunger is at most this value
    DISPATCH_MAX_HUNGER = 2
    # Minimum HP for a warrior to be sent to the cave
    WARRIOR_MIN_HP = 3
    # Retreat from the cave at or below this HP
    RETREAT_HP = 1
    # Wheat kept in reserve after spawning, for next step's meals
    WHEAT_RESERVE = 2
    WARRIOR_SPAWN_COST = 12
    # Spawning is only worthwhile early in the 30-step game
    SPAWN_STEP_LIMIT = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(environment.farm.wheat, 0)

        # 1) Feed the most hungry villagers first, limited by available wheat
        needy = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        eaters = needy[:wheat]
        eater_ids = set(id(c) for c in eaters)
        remaining_wheat = wheat - len(eaters)

        # 2) Among the rest, pick warriors for the cave and idle farmers for spawning
        rest = [c for c in components if id(c) not in eater_ids]
        cave_ids = set()
        for c in rest:
            if (
                c.role == "Warrior"
                and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
                and c.hp >= self.WARRIOR_MIN_HP
            ):
                cave_ids.add(id(c))

        idle_farmers = [c for c in rest if c.role == "Farmer"]

        spawn_ids = set()
        if (
            step < self.SPAWN_STEP_LIMIT
            and len(idle_farmers) >= 2
            and remaining_wheat >= self.WARRIOR_SPAWN_COST + self.WHEAT_RESERVE
        ):
            for c in idle_farmers[:2]:
                spawn_ids.add(id(c))

        # 3) Assign every component exactly once
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif cid in cave_ids:
                environment.assign_group(c, "cave")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hungry = c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD
            if c.role == "Warrior":
                weak = c.hp <= self.RETREAT_HP
            else:
                weak = c.hp <= 2

            if hungry or weak:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```