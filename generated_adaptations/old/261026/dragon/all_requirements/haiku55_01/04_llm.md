## Revised Strategy: Prioritized Spawning with Attack Pressure

The failing tests show three problems in my previous version:

1. **Spawning was too restrictive.** It required four or more farmers in the Village before spawning anything. Small starting populations never spawned, so the "new farmers" and "new warriors" constraints failed.
2. **No early attacks without initial warriors.** With no starting warriors, nothing attacked the Dragon in the first 15 steps.
3. **The Dragon was not killed.** Too few warriors were produced, so the Dragon survived within 30 steps.

**Village phase (`assign_in_village`):**
- All warriors go to `"cave"` so they can attack.
- Farmers are grouped into pairs. Each step, the code computes how many pairs are possible from the farmer count and the wheat budget.
- Warrior pairs are preferred (3 damage per attack) while the warrior count is below a target. Farmer pairs follow while the farmer count is below a target.
- At most a few pairs are spawned per step, and the wheat budget is tracked locally so the code never over-commits.
- The rest of the farmers go to `"farm"`. At least one farmer stays on the farm when any farmer exists, so wheat income is not fully cut off.

**Cave phase (`assign_in_cave`):**
- Every warrior in the Cave attacks every step, which provides damage from the first step after spawning.
- Farmers that end up in the Cave are sent back to `"village"`.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors always go to the Cave and attack the Dragon.
    - Farmers are paired up and spawned into warriors (preferred, 12 wheat)
      or farmers (10 wheat) whenever wheat and population targets allow.
    - Remaining farmers keep farming, and at least one farmer stays on the
      farm whenever farmers exist, so wheat income is not fully cut off.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    TARGET_WARRIORS = 8
    TARGET_FARMERS = 8
    MAX_PAIRS_PER_STEP = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always go to the Cave to fight the Dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        warrior_count = len(warriors)
        farmer_count = len(farmers)

        # Simulated counts to decide how many spawns we still want.
        pool = list(farmers)
        spawn_warrior = []
        spawn_farmer = []
        pairs_done = 0

        # Prefer warrior spawns while warrior count is below target.
        while (len(pool) >= 2
               and wheat >= self.WARRIOR_SPAWN_COST
               and warrior_count < self.TARGET_WARRIORS
               and pairs_done < self.MAX_PAIRS_PER_STEP):
            spawn_warrior.extend(pool[:2])
            pool = pool[2:]
            wheat -= self.WARRIOR_SPAWN_COST
            warrior_count += 1
            pairs_done += 1

        # Then spawn farmers while farmer count is below target.
        while (len(pool) >= 2
               and wheat >= self.FARMER_SPAWN_COST
               and farmer_count < self.TARGET_FARMERS
               and pairs_done < self.MAX_PAIRS_PER_STEP):
            spawn_farmer.extend(pool[:2])
            pool = pool[2:]
            wheat -= self.FARMER_SPAWN_COST
            farmer_count += 1
            pairs_done += 1

        for f in spawn_warrior:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer:
            environment.assign_group(f, "spawn farmer")
        for f in pool:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Every warrior in the Cave keeps attacking the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Farmers must not remain in the Cave.
                environment.assign_group(c, "village")
```