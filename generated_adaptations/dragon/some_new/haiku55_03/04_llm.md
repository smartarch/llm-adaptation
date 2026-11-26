## Diagnosis

The failing tests are all `test_no_required_constraints_violated_at_the_end`, and the failure message says the game ended without the Dragon being killed. The 33% win rate points the same way. The previous strategy was too slow and too thin:

- **Too few attackers.** Only two farmers were used to spawn, and only when wheat was at least 15, so the warrior count grew slowly.
- **Too little damage per step.** Every warrior attack is 3 damage, so the Dragon's 100 HP needs about 34 warrior attacks. The old strategy often had too few warriors in the Cave to reach that.
- **Attack gaps.** When the Cave had few warriors, the Dragon regenerated 5 HP in the gaps, which slowed the kill further.

## Revised strategy

**Spawning more warriors.** Spawns use the "for every two villagers in the group" rule, so the spawn group can hold 2 farmers per warrior. Each step the code spawns up to 2 warriors, limited by the wheat budget after reserving wheat for meals and by the number of available farmers. Two farmers are kept on the farm wherever possible so that wheat income continues.

**Feeding.** Any villager (farmer or warrior) with `steps_since_meal >= 3` eats in the Village. Eating takes priority over spawning and dispatching, and the wheat for meals is subtracted from the spawn budget.

**Dispatch.** Fed, healthy warriors (`steps_since_meal < 3`, `hp > 2`) go to the Cave. Warriors that are hurt or badly hit stay on the farm, where they still produce wheat. Farmers never go to the Cave, because their 4 HP and 1 damage make them poor attackers.

**Cave.** Warriors attack as long as they are fed and healthy. They rotate back to the Village at `steps_since_meal >= 3` or `hp <= 2`. With several warriors on staggered cycles, the Dragon is attacked almost every step, which prevents regeneration.

**Why the constraints hold.** A warrior eats in the Village, spends at most 3 steps in the Cave, and then returns and eats again. This keeps every villager well under the 6-step starvation limit, including the round-trip step.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast-kill strategy: maximize warrior output and keep the Dragon under
    continuous attack, while keeping every villager fed.

    - Villagers with steps_since_meal >= FEED_THRESHOLD eat in the Village.
    - Spare farmers spawn warriors (2 farmers per warrior, 12 wheat each),
      limited by the wheat left after meals and by a per-step spawn cap.
    - Fed, healthy warriors go to the Cave to attack.
    - Warriors leave the Cave when hungry or badly hurt; farmers never fight.
    """

    FEED_THRESHOLD = 3        # eat when steps_since_meal reaches this
    LOW_HP = 2                # warriors at or below this HP stop fighting
    WARRIOR_SPAWN_COST = 12
    MAX_SPAWNS_PER_STEP = 2   # warriors spawned per step at most
    MIN_FARMERS_FARMING = 1   # keep at least this many farmers producing wheat

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat, rest = [], []
        for c in components:
            if c.steps_since_meal >= self.FEED_THRESHOLD:
                eat.append(c)
            else:
                rest.append(c)

        # Wheat left after paying for this step's meals.
        budget = wheat - len(eat)

        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]

        # Decide how many warriors to spawn this step.
        # Each spawn needs 2 farmers in the spawn group; keep some farmers farming.
        max_by_wheat = max(0, budget // self.WARRIOR_SPAWN_COST)
        max_by_farmers = max(0, (len(farmers) - self.MIN_FARMERS_FARMING) // 2)
        num_spawns = min(self.MAX_SPAWNS_PER_STEP, max_by_wheat, max_by_farmers)

        spawn_group = farmers[: 2 * num_spawns]
        spawn_ids = {id(c) for c in spawn_group}

        # Warriors that are fed and healthy go to the Cave; the rest farm.
        cave_group, farm_group = [], []
        for c in warriors:
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