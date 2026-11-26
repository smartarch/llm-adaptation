## Diagnosis

The last run won 33% of games in an average of 25 steps. That is faster than before, but several seeds still run out of steps. The remaining bottlenecks are:

- **Spawning is limited to farmers.** Spawn groups can contain any two villagers, but the previous version used only idle farmers. Idle warriors on the farm could be paired too, which turns spare hands into attackers sooner.
- **The wheat reserve is too conservative.** Keeping a flat 2-wheat reserve is safe for meals, but it also blocks spawns when wheat is only slightly short. The reserve should track the real number of meals due next step.
- **Cave cohorts are not rotated tightly.** Warriors that finish a cave stint and eat should be sent back out on the next step, so the Cave stays occupied.

## Revised strategy: count the real meal reserve, spawn from any spare villagers

1. **Feed first, budgeted.** Villagers at `steps_since_meal >= 2` eat, most hungry first, limited by wheat stock.
2. **Reserve only what is needed.** The reserve for next step is the number of villagers that will reach hunger 2 or more, approximated by the cave warriors plus the eaters, instead of a flat constant. This lets spawns happen whenever the wheat is really available.
3. **Spawn from spare villagers.** Villagers not eating and not needed in the cave are paired into "spawn warrior" groups, preferring farmers. A farmer is kept on the farm when the pool is small so wheat income continues.
4. **Dispatch fresh warriors.** Warriors with `steps_since_meal <= 1` and `hp >= 2` go to the cave, to keep the Dragon under continuous attack.
5. **Cave rotation.** Warriors attack while `steps_since_meal < 4` and `hp > 1`. They return to eat at hunger 4, which keeps every villager under the 6-step starvation limit.
6. **Farmers never enter the cave.** The Dragon's area attack would kill them.
7. **Complete assignment.** Every component is assigned exactly once per method.

I have not run the simulation, so the improvement is an estimate. The at-the-end tests and the win rate should be rechecked.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Villagers at or above this hunger are sent to eat in the village
    EAT_THRESHOLD = 2
    # Cave warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village warriors at or below this hunger are dispatched to the cave
    DISPATCH_MAX_HUNGER = 1
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 2
    # Cave warriors at or below this HP retreat
    WARRIOR_RETREAT_HP = 1
    WARRIOR_SPAWN_COST = 12
    # Keep at least this many farmers working the farm for wheat income
    MIN_FARMERS_ON_FARM = 1

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

        rest = [c for c in components if id(c) not in eater_ids]

        # 2) Send every fresh, healthy warrior to the cave
        cave_list = [
            c for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        ]
        cave_ids = set(id(c) for c in cave_list)

        # 3) Spawn from the remaining villagers, farmers first.
        #    Reserve wheat for next step's meals: villagers that will need food soon.
        upcoming_meals = sum(
            1 for c in components
            if c.steps_since_meal + 1 >= self.EAT_THRESHOLD
        )
        reserve = max(upcoming_meals - len(eaters), 0)
        affordable = (remaining_wheat - reserve) // self.WARRIOR_SPAWN_COST

        spare = [c for c in rest if id(c) not in cave_ids]
        spare.sort(key=lambda c: 0 if c.role == "Farmer" else 1)
        spare_farmers = [c for c in spare if c.role == "Farmer"]

        # Keep the minimum farmers working, then spawn in pairs
        pool = len(spare) - self.MIN_FARMERS_ON_FARM
        spawns = min(max(affordable, 0), max(pool, 0) // 2)

        spawn_ids = set(id(c) for c in spare[: 2 * spawns])

        # 4) Assign every component exactly once
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
                weak = c.hp <= self.WARRIOR_RETREAT_HP
            else:
                # Farmers should not be in the cave; send any back to the farm
                weak = True

            if hungry or weak:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```