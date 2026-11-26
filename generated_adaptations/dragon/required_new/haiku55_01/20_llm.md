## Diagnosis

The eating and assignment tests pass. The failing test is the win condition: the Dragon is still alive after 30 steps in every seed. Since the assignment logic is stable, the remaining problem is damage throughput. Specifically:

- **Cave slots go unused.** Warriors are dispatched only at hunger 2 or less, so some steps have empty Cave slots. Each step with no attack lets the Dragon regenerate 5 HP.
- **Wheat is spent on eating too early.** Eating at hunger 2 consumes wheat that could fund spawns. The 6-step starvation limit allows eating at hunger 4 and still staying safe.
- **Retreat is too late for warriors at 1 HP.** Warriors at 2 HP are sent back only at 1 HP, so the Dragon's area attack can take them out in the Cave. Retreating at 2 HP keeps them alive to attack again.

I can't run the simulation, so I can't confirm these changes fix the at-the-end tests. If they still fail, the most likely remaining cause is that 100 HP cannot be dealt in 30 steps with the starting villagers and wheat. In that case, the next step is to log attacks per step from a run.

## Revised strategy

1. **Eat at hunger 4.** Villagers at `steps_since_meal >= 4` go to "eat", most hungry first, limited by wheat. This is safe under the 6-step limit and saves wheat.
2. **Fill the Cave every step.** Fed warriors (`steps_since_meal <= 2`, `hp >= 3`) go to the Cave, up to a cap large enough to keep it occupied.
3. **Spawn warriors from spare farmers.** Spawns use the wheat left after this step's meals. At least one farmer always stays on the farm.
4. **Retreat earlier.** Cave warriors return at hunger 4 or at 2 HP, so they survive to attack again.
5. **Farmers stay home.** Farmers never enter the Cave.
6. **Complete assignment.** Every component is assigned exactly once per method.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Villagers at or above this hunger are sent to eat (safe under the 6-step limit)
    EAT_THRESHOLD = 4
    # Cave warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village warriors at or below this hunger may be dispatched to the cave
    DISPATCH_MAX_HUNGER = 2
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 3
    # Cave warriors at or below this HP retreat (area attacks deal 1 damage)
    WARRIOR_RETREAT_HP = 2
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

        # 2) Fill the cave with fed, healthy warriors
        cave_list = [
            c for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        ]
        cave_ids = set(id(c) for c in cave_list)

        # 3) Spawn warriors from spare farmers using wheat left after this step's meals
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