## Diagnosis

The eating and assignment tests pass, so the remaining failure is still the win condition. Every version so far has left the Dragon alive after 30 steps. Looking at the previous code, I see three likely causes:

- **Spawning starves the economy.** Spawns pull farmers off the farm, which lowers wheat income. The spawn logic then fails to find the 12 wheat it needs, so the warrior count stalls.
- **Warriors are cycled too slowly.** A warrior that just ate is sent out only at hunger 0 or 1, so some steps have an empty Cave, and the Dragon regenerates 5 HP on each of those steps.
- **Retreat is too cautious.** Warriors leave at 1 HP, and the Dragon's area attack (40% per attacking step) can then remove attackers the Cave needs.

I can't run the simulation, so these are estimates. The changes below target them directly.

## Revised strategy

1. **Protect the economy.** Keep at least two farmers on the farm whenever possible, and spawn only from farmers beyond that minimum. Spawns use only wheat that remains after this step's meals and a reserve for the meals due next step.
2. **Feed first, by hunger.** Villagers at `steps_since_meal >= 2` eat, most hungry first, limited by wheat stock.
3. **Keep the Cave occupied.** Every fed warrior (`steps_since_meal <= 2`, `hp >= 2`) that is not eating goes to the Cave. Warriors at hunger 2 still have room for the trip out and back.
4. **Attack while safe.** Cave warriors attack while `steps_since_meal < 4` and `hp > 1`. They return at hunger 4, which keeps them below the 6-step starvation limit after the one-step trip back.
5. **Farmers stay home.** Farmers never enter the Cave, because the Dragon's area attack would kill them.
6. **Complete assignment.** Every component is assigned exactly once per method.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Villagers at or above this hunger are sent to eat in the village
    EAT_THRESHOLD = 2
    # Cave warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village warriors at or below this hunger are dispatched to the cave
    DISPATCH_MAX_HUNGER = 2
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 2
    # Cave warriors at or below this HP retreat
    WARRIOR_RETREAT_HP = 1
    # Farmers kept on the farm for wheat income
    MIN_FARMERS_ON_FARM = 2
    # Wheat reserved for next step's meals
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
        cave_list = [
            c for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        ]
        cave_ids = set(id(c) for c in cave_list)

        # 3) Spawn from spare farmers while wheat covers the cost plus reserve
        spare_farmers = [c for c in rest if c.role == "Farmer" and id(c) not in cave_ids]
        pool = len(spare_farmers) - self.MIN_FARMERS_ON_FARM
        affordable = (remaining_wheat - self.WHEAT_RESERVE) // self.WARRIOR_SPAWN_COST
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