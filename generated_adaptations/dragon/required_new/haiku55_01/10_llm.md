## Diagnosis

The at-the-end test still fails, so the Dragon is not dying within 30 steps. The eating and assignment logic now passes its tests, so the remaining problem is damage throughput. The previous versions had three weaknesses:

- **Spawning was too restrained.** Warriors are the only real damage source (3 per attack, against 1 for farmers), and each step with no attack lets the Dragon regenerate 5 HP. The previous versions spawned at most one warrior at a time and kept too many farmers idle on the farm.
- **Warrior cycles were uneven.** Warriors were sent out only when their hunger was 0 or 1, which left the Cave empty on some steps.
- **Spawned warriors were not used quickly.** New warriors appear fully fed, so they should go straight to the Cave.

## Revised strategy: maximize warrior output, keep the Cave continuously attacked

1. **Spawn warriors whenever wheat allows.** Each step, after reserving wheat for this step's meals plus a 2-wheat buffer for the next step, spawn as many warriors as the wheat covers (up to two per step). Use idle farmers in pairs and keep two farmers on the farm to maintain wheat income.
2. **Feed first, by hunger.** Villagers with `steps_since_meal >= 2` eat, most hungry first, limited by the wheat stock.
3. **Dispatch every fresh warrior.** Warriors with `steps_since_meal <= 1` and `hp >= 2` go to the Cave. Warriors that just spawned are fed, so they go straight out.
4. **Stagger cave rotations.** Cave warriors attack while `steps_since_meal < 4` and `hp > 1`. They return to eat at hunger 4, so they never reach the 6-step limit even after the one-step trip back.
5. **Farmers stay home.** Farmers never enter the Cave, because the Dragon's area attack would kill them and their wheat is needed.
6. **Complete assignment.** Every component is assigned exactly once per method.

This is still not guaranteed to win. The Dragon's counterattacks (40% area damage, 20% chance to eat a villager per attacking step) can remove attackers, and 100 HP needs about 34 warrior hits within 30 steps. This version gives the highest sustained damage I can get within the starvation rule.

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
    # Keep at least this many farmers on the farm for wheat income
    MIN_FARMERS_ON_FARM = 2
    # Maximum warriors spawned per step
    MAX_SPAWNS_PER_STEP = 2

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
        cave_ids = set(
            id(c) for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        )

        # 3) Spawn warriors with idle farmers, as many as the wheat allows
        idle_farmers = [c for c in rest if c.role == "Farmer"]
        spare_farmers = len(idle_farmers) - self.MIN_FARMERS_ON_FARM
        affordable = (remaining_wheat - self.WHEAT_RESERVE) // self.WARRIOR_SPAWN_COST
        spawns = min(self.MAX_SPAWNS_PER_STEP, spare_farmers // 2, max(affordable, 0))

        spawn_ids = set()
        for c in idle_farmers[: 2 * spawns]:
            spawn_ids.add(id(c))

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