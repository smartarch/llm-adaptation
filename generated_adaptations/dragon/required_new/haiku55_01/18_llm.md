## Diagnosis

The eating and assignment tests pass, so the remaining failure is the win condition: the Dragon survives 30 steps. The previous versions had three problems:

- **Wasted wheat on eating.** Villagers ate whenever their hunger reached 2, which spent about a third of a wheat per villager per step. The limit is 6 steps, so eating at 4 is safe and saves wheat for spawning.
- **Too few attackers at once.** Warriors left the Cave at hunger 4, but the dispatch rule was strict. Some steps had empty Cave slots, and the Dragon regenerated 5 HP on each of those steps.
- **Spawn reserve was too big.** Reserving wheat for every villager's next meal blocked spawns that the economy could afford. Spawn groups only tie up two villagers, and the wheat cost is the real constraint, so spawns should use whatever wheat remains after this step's meals.

## Revised strategy

1. **Eat late, but safely.** Villagers eat when `steps_since_meal >= 4`, so they never reach the 6-step limit. If wheat is short, the most hungry eat first.
2. **Spawn with leftover wheat.** After this step's meals, spawn as many warriors as the remaining wheat covers (12 each). Use spare farmers in pairs, and keep at least one farmer on the farm for income.
3. **Fill the Cave.** Every fed, healthy warrior in the Village (hunger <= 2, HP >= 2) goes to the Cave, including new spawns.
4. **Cycle warriors at hunger 4.** Cave warriors attack while hunger is below 4 and HP is above 1. They return at hunger 4, arrive at 5, and eat on arrival, which stays below the 6-step limit.
5. **Farmers stay home.** Farmers never enter the Cave, because the Dragon's area attack would kill them.
6. **Complete assignment.** Every component is assigned exactly once per method.

I could not run the simulation, so I can't confirm the win rate. If the at-the-end tests still fail, the next step is to measure how many warrior-attack steps occur per run.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Villagers at or above this hunger eat in the village (stays below the 6-step limit)
    EAT_THRESHOLD = 4
    # Cave warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village warriors at or below this hunger are dispatched to the cave
    DISPATCH_MAX_HUNGER = 2
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 2
    # Cave warriors at or below this HP retreat
    WARRIOR_RETREAT_HP = 1
    # Farmers kept on the farm for wheat income
    MIN_FARMERS_ON_FARM = 1
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
        cave_list = [
            c for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        ]
        cave_ids = set(id(c) for c in cave_list)

        # 3) Spawn with the wheat left after this step's meals, using spare farmers in pairs
        spare_farmers = [c for c in rest if c.role == "Farmer" and id(c) not in cave_ids]
        pool = len(spare_farmers) - self.MIN_FARMERS_ON_FARM
        affordable = remaining_wheat // self.WARRIOR_SPAWN_COST
        spawns = min(max(affordable, 0), max(pool, 0) // 2)

        spawn_ids = set(id(c) for c in spare_farmers[: 2 * spawns])

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