## Diagnosis

The 0% win rate has three causes:

1. **Spawning almost never happened.** The old code required at least 4 farmers (2 spawners plus 2 kept on the farm) before it would spawn anything. Starting groups are small, so the warrior pipeline stayed empty.
2. **Too little damage.** Only the starting warriors attacked, at 3 damage each. Against 50 HP, that is roughly 17 warrior hits, and the Dragon's 40% group hits and 20% eat chance wiped out the small force before it could finish the job.
3. **Wheat was spent poorly.** The code kept spawning farmers that added no damage, and it had no rule to prioritize the warriors that do the work.

## Revised strategy

**Village (`assign_in_village`)**
- Warriors always go to the Cave, so damage starts at step 1.
- Farmers stay on the farm by default, since they produce the wheat that funds spawns.
- Spawning is planned from the wheat budget with a clear priority:
  - **Warriors first.** If wheat covers a warrior (12) and there are enough farmers, two farmers are placed in `"spawn warrior"`.
  - **A few farmers early.** To meet the farmer-spawn requirement, one farmer pair goes to `"spawn farmer"` while fewer than two farmers have been spawned and wheat covers it (10).
  - The rule "keep at least one farmer farming" is relaxed to "only take a pair if at least 3 farmers are available," so wheat income never falls to zero.
- Spawn counts are tracked across steps, so the farmer quota is actually met.

**Cave (`assign_in_cave`)**
- Every warrior attacks. Warrior damage is the only damage source that the requirements allow, so maximizing warrior count and keeping them alive is the goal.
- Any farmer found in the Cave is sent back to the Village.

Every component is re-assigned on every step.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warriors attack the Dragon from step 1 and are reinforced with
    warrior spawns whenever wheat allows. Farmers keep the wheat flowing
    and a small number of farmers are spawned early.
    """

    SPAWN_GROUP_SIZE = 2
    WARRIOR_WHEAT_COST = 12
    FARMER_WHEAT_COST = 10
    MIN_FARMERS_LEFT_FARMING = 1
    MAX_FARMER_SPAWNS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors go to the Cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        wheat = environment.farm.wheat
        pool = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Prefer warrior spawns, since warriors do the damage.
        if (wheat >= self.WARRIOR_WHEAT_COST
                and len(pool) >= self.SPAWN_GROUP_SIZE + self.MIN_FARMERS_LEFT_FARMING):
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_warrior_group.append(pool.pop())
            wheat -= self.WARRIOR_WHEAT_COST

        # Early farmer spawns to meet the farmer-growth requirement.
        if (self.farmers_spawned < self.MAX_FARMER_SPAWNS
                and wheat >= self.FARMER_WHEAT_COST
                and len(pool) >= self.SPAWN_GROUP_SIZE + self.MIN_FARMERS_LEFT_FARMING):
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_farmer_group.append(pool.pop())
            wheat -= self.FARMER_WHEAT_COST
            self.farmers_spawned += 1

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")
        for f in pool:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers have 4 HP and deal 1 damage; keep them out of the Cave.
                environment.assign_group(c, "village")
```