## Diagnosis

The eating and assignment tests pass, so the remaining failure is the win condition: the Dragon is not dead within 30 steps. Three things limit damage output in the previous versions:

- **Spawning was capped too low.** Each step spawned at most two warriors, and only from idle farmers beyond a fixed minimum. Warriors are the only real damage source (3 per hit), so the warrior count has to grow quickly.
- **Farmers were kept idle when wheat was short.** The spawn cost is 12 wheat per warrior, while a farmer produces 5 wheat per step. Keeping the economy running has to come before spawning, not compete with it.
- **Spawn pairs were not sized to the wheat.** A spawn needs two villagers in the "spawn warrior" group plus 12 wheat. The number of spawns should be the smaller of what wheat can pay for and what the idle farmers can pair up to, with no artificial cap.

## Revised strategy: economy first, then warrior burst

1. **Economy phase:** While wheat is below the cost of a spawn plus the next step's meal reserve, every idle farmer works the farm.
2. **Burst phase:** Once wheat covers a spawn, idle farmers are paired into "spawn warrior" groups as many times as wheat allows. The number of spawns is `min(wheat_after_meals_minus_reserve // 12, idle_farmers // 2)`.
3. **Feed first, by hunger:** Villagers at `steps_since_meal >= 2` eat, most hungry first, limited by the wheat stock, so there is never an over-budget meal order.
4. **Dispatch every fed, healthy warrior:** Warriors with `steps_since_meal <= 1` and `hp >= 2` go to the Cave, including those spawned this step.
5. **Cave rotation:** Warriors attack while `steps_since_meal < 4` and `hp > 1`. They return to eat at hunger 4, which keeps them under the 6-step starvation limit after the trip back.
6. **Farmers stay home:** Farmers never enter the Cave, since the Dragon's area attack would kill them.
7. **Complete assignment:** Every component is assigned exactly once per method.

I can't verify the win rate without running the simulation, and the Dragon's counterattacks can still remove attackers. This version is the highest-throughput approach I can design within the starvation rule, and it should be checked against the at-the-end tests.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: villagers at or above this hunger are sent to eat
    EAT_THRESHOLD = 2
    # Cave: warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village: warriors at or below this hunger are dispatched to the cave
    DISPATCH_MAX_HUNGER = 1
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 2
    # Cave: warriors at or below this HP retreat
    WARRIOR_RETREAT_HP = 1
    # Wheat kept back for next step's meals
    WHEAT_RESERVE = 2
    WARRIOR_SPAWN_COST = 12

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

        # 2) Send every fed, healthy warrior to the cave
        cave_ids = set(
            id(c) for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        )

        # 3) Burst phase: pair idle farmers into spawns as wheat allows.
        #    Economy phase: if wheat cannot cover a spawn plus reserve, farmers keep farming.
        idle_farmers = [c for c in rest if c.role == "Farmer"]
        affordable = (remaining_wheat - self.WHEAT_RESERVE) // self.WARRIOR_SPAWN_COST
        spawns = min(max(affordable, 0), len(idle_farmers) // 2)

        spawn_ids = set(id(c) for c in idle_farmers[: 2 * spawns])

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