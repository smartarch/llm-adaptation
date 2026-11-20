## Diagnosis of the last run

The previous version almost never spawned. Its spawn rule required at least 4 farmers in the village (2 to spawn plus 2 kept on the farm), and the starting party probably has fewer. Nothing spawned, the warriors died or stayed out of the fight, and the Dragon kept its full 100 HP.

The "keep 2 farmers farming" rule was also unnecessary. A spawn takes a farmer off the farm for only one step, since the group is re-assigned every step. So the cost of spawning is small, and the benefit is large.

## Revised strategy

1. **Feed first, by urgency.** Warriors with `steps_since_meal >= 1` in the Village eat. Farmers eat at 3 steps. If wheat is short, the most hungry villagers eat first.
2. **Reserve wheat for meals.** Keep a reserve of about half the warriors plus 1 for the next step's meals. Spawning uses only the wheat above this reserve.
3. **Spawn warriors whenever affordable.** Each step, every pair of idle farmers is turned into a "spawn warrior" group while wheat above the reserve is at least 12. No minimum farmer count is required. Any leftover farmers farm.
4. **Warrior cycle.** Fresh warriors in the Village go to the Cave. In the Cave, warriors attack while `steps_since_meal < 3`, then return to the Village to eat and come back. This keeps each warrior within the 6-step starvation limit.
5. **Farmers stay in the Village.** They never enter the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Villagers in the Village eat first, most hungry first, limited by available wheat.
    - A wheat reserve is kept for upcoming meals; the rest is used to spawn warriors.
    - Every affordable pair of idle farmers spawns a warrior (a spawn takes only one step
      away from the farm, so the economy keeps running).
    - Warriors attack in the Cave while steps_since_meal < 3, then return to eat and come back.
    - Farmers never enter the Cave.
    """

    WARRIOR_LEAVE_CAVE_AT = 3
    FARMER_EAT_AT = 3
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Meals: warriors that are not fresh, farmers at the threshold; most hungry first.
        candidates = [c for c in warriors if c.steps_since_meal >= 1]
        candidates += [c for c in farmers if c.steps_since_meal >= self.FARMER_EAT_AT]
        candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)

        eaters = candidates[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        for c in eaters:
            environment.assign_group(c, "eat")
        wheat -= len(eaters)

        idle_farmers = [c for c in farmers if id(c) not in eater_ids]
        fresh_warriors = [c for c in warriors if id(c) not in eater_ids]

        # 2) Reserve wheat for the next step's meals.
        reserve = len(warriors) // 2 + 1

        # 3) Spawn warriors from pairs of idle farmers while affordable.
        spawn_ids = set()
        pool = list(idle_farmers)
        while len(pool) >= 2 and wheat - reserve >= self.WARRIOR_COST:
            pair = pool[:2]
            pool = pool[2:]
            for c in pair:
                environment.assign_group(c, "spawn warrior")
                spawn_ids.add(id(c))
            wheat -= self.WARRIOR_COST

        # 4) Fresh warriors go to the Cave to fight.
        for c in fresh_warriors:
            environment.assign_group(c, "cave")

        # 5) Remaining farmers farm.
        for c in idle_farmers:
            if id(c) not in spawn_ids:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.WARRIOR_LEAVE_CAVE_AT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```