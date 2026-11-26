## Diagnosis

The new failures come from three problems in the previous version.

1. **Spawning was too restrictive.** `max_by_farmers` reserved one farmer and required pairs of the rest, so with two idle farmers the code never spawned. This broke the optional "spawn instead of farming when there are fewer than 5 villagers" rule.
2. **Warriors were not replaced when the Cave was empty.** With no warriors in the Village or Cave, nothing triggered a spawn, so the Dragon went unattacked for many steps and the game was lost.
3. **Too little damage overall.** Spawns were capped at two per step and many warriors were left on the farm, so the Dragon was not killed within 30 steps.

## Revised strategy

**Spawn policy.** Each step, the code spawns as many warriors as the constraints allow, up to 3 per step. A spawn is allowed only when two villagers are in the spawn pool and the wheat left after this step's meals still covers 12 wheat per warrior plus one meal for every villager after the spawn. Farmers form the spawn pool first. Warriors fill in only if fewer than two farmers are available. This means the code never leaves two free farmers idle when the wheat reserve allows a spawn, and it always replaces warriors quickly when none are left.

**Feeding.** Any villager with `steps_since_meal >= 3` eats in the Village. Meal wheat is paid before spawn wheat is counted.

**Dispatch.** Fed, healthy warriors (`hp > 2`, `steps_since_meal < 3`) go to the Cave, and all other warriors and farmers stay on the farm. Warriors in the spawn group are excluded from the Cave.

**Cave.** Warriors attack while they are fed and above 2 HP. Those that are hungry or hurt return to the Village. Farmers never attack. The Dragon's 20% chance per attack to eat a random villager is less damaging with more warriors present, since each attack step carries the same risk regardless of how many warriors attack, so the strategy keeps as many warriors as possible in the Cave.

**Constraints.** Every villager eats within 3 steps of its last meal, and the Cave stay is at most 3 steps, so the 6-step starvation limit holds. Spawns are reserved against future meals, so wheat does not run out.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy with aggressive warrior spawning.

    - Villagers with steps_since_meal >= FEED_THRESHOLD eat in the Village.
    - Idle farmers form spawn pairs (2 per warrior, 12 wheat each). Spawns
      happen whenever wheat still covers one meal per villager afterwards.
    - Fed, healthy warriors attack in the Cave; hungry or hurt warriors
      return to the Village. Farmers never fight.
    """

    FEED_THRESHOLD = 3       # eat when steps_since_meal reaches this
    LOW_HP = 2               # warriors at or below this HP stop fighting
    WARRIOR_COST = 12
    MAX_SPAWNS_PER_STEP = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        population = len(environment.farmers) + len(environment.warriors)

        eat, rest = [], []
        for c in components:
            if c.steps_since_meal >= self.FEED_THRESHOLD:
                eat.append(c)
            else:
                rest.append(c)

        # Wheat available after paying for this step's meals.
        budget = wheat - len(eat)

        # Spawn pool: idle farmers first, then idle warriors if needed.
        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]
        pool = farmers + warriors

        spawn_group = []
        spawns = 0
        while (
            spawns < self.MAX_SPAWNS_PER_STEP
            and len(pool) - len(spawn_group) >= 2
        ):
            new_cost = self.WARRIOR_COST * (spawns + 1)
            # Keep one meal of wheat for every villager after the spawn.
            if budget - new_cost < population + spawns + 1:
                break
            # Take two villagers for this spawn.
            spawn_group.extend(pool[len(spawn_group): len(spawn_group) + 2])
            spawns += 1

        spawn_ids = {id(c) for c in spawn_group}

        # Fed, healthy warriors go to the Cave; everyone else farms.
        cave_group, farm_group = [], []
        for c in warriors:
            if id(c) in spawn_ids:
                continue
            if c.hp > self.LOW_HP and c.steps_since_meal < self.FEED_THRESHOLD:
                cave_group.append(c)
            else:
                farm_group.append(c)
        for c in farmers:
            if id(c) not in spawn_ids:
                farm_group.append(c)

        for c in eat:
            environment.assign_group(c, "eat")
        for c in spawn_group:
            environment.assign_group(c, "spawn warrior")
        for c in cave_group:
            environment.assign_group(c, "cave")
        for c in farm_group:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.FEED_THRESHOLD or c.hp <= self.LOW_HP:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```