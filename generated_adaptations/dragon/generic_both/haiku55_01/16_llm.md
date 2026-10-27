## Revised strategy: warrior-first allocation with a larger army cap

**Diagnosis:** The last two versions finished in 19.3 and 20.3 steps. The difference is small and may partly be simulation noise, but the two runs suggest that the number of warriors attacking each step is what matters most. The Dragon needs about 34 warrior hits, so the fight ends roughly when the attacking army reaches its steady size. The 20.3 version stopped at 4 farmers and 14 warriors, but it never built a larger army. Its warrior cap was also reached only after the farm was complete, so the army grew more slowly.

**Changes:**

1. **Two-farmer minimum, then warriors.** The task requires two of each role, so the code still builds two farmers first. Warriors then take every idle farmer pair that the wheat budget allows.
2. **Larger warrior cap.** The warrior target is raised from 14 to 16. Wheat, not the cap, limits growth in most steps, so the higher cap only matters late in the fight and does not slow the early build-up.
3. **Extra farmers last, with a higher cap.** Farmers beyond the minimum are built only from wheat left after warrior spawns. The cap is raised from 4 to 5 so that extra wheat is still converted into farm output when the warrior cap is reached.
4. **Unchanged safety rules.** Warriors eat at a meal clock of 3 and walk home from the Cave at 4, so no warrior is sent out hungry or starves. Meals are capped by the wheat stock, the Cave always keeps at least one attacker, and every villager is assigned exactly once.

I can't run the simulator here, so these numbers are a hypothesis to check against the win-time measurement.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors eat in the Village once their meal clock reaches this value.
    WARRIOR_EAT_THRESHOLD = 3
    # Warriors in the Cave walk home once their meal clock reaches this value.
    CAVE_RETURN_THRESHOLD = 4
    # Population targets: two farmers first, then warriors, then extra farmers.
    MIN_FARMERS = 2
    TARGET_WARRIORS = 16
    TARGET_FARMERS = 5
    FARMER_COST = 10
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warriors that stay in the Cave to attack. Returners are counted in the
        # Village phase when they arrive, so they are not counted here.
        self._cave_attackers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1. Collect everyone who needs a meal now.
        wants_food = []
        for c in components:
            if c.role == "Farmer":
                needs = c.steps_since_meal >= self.FARMER_EAT_THRESHOLD
            else:
                needs = c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
            if needs:
                wants_food.append(c)

        # Feed the most urgent first, never more villagers than the wheat stock allows.
        wants_food.sort(key=lambda c: c.steps_since_meal, reverse=True)
        eaters = wants_food[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        budget = wheat - len(eaters)

        non_eaters = [c for c in components if id(c) not in eater_ids]
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]

        # 2. Plan spawns from pairs of idle farmers.
        total_farmers = len(farmers)
        total_warriors = len(warriors) + self._cave_attackers

        spawn_plan = {}  # id(component) -> spawn group name
        pool = list(idle_farmers)

        # Phase A: the minimum farm.
        need_farmers = max(0, self.MIN_FARMERS - total_farmers)
        n_pairs = min(len(pool) // 2, budget // self.FARMER_COST, need_farmers)
        for c in pool[: 2 * n_pairs]:
            spawn_plan[id(c)] = "spawn farmer"
        pool = pool[2 * n_pairs:]
        budget -= n_pairs * self.FARMER_COST
        total_farmers += n_pairs

        # Phase B: warriors, which deal the damage.
        need_warriors = max(0, self.TARGET_WARRIORS - total_warriors)
        n_pairs = min(len(pool) // 2, budget // self.WARRIOR_COST, need_warriors)
        for c in pool[: 2 * n_pairs]:
            spawn_plan[id(c)] = "spawn warrior"
        pool = pool[2 * n_pairs:]
        budget -= n_pairs * self.WARRIOR_COST

        # Phase C: extra farmers only with leftover wheat.
        need_farmers = max(0, self.TARGET_FARMERS - total_farmers)
        n_pairs = min(len(pool) // 2, budget // self.FARMER_COST, need_farmers)
        for c in pool[: 2 * n_pairs]:
            spawn_plan[id(c)] = "spawn farmer"

        # 3. Assign every villager to exactly one group.
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_plan:
                environment.assign_group(c, spawn_plan[cid])
            elif c.role == "Warrior" and c.steps_since_meal < self.WARRIOR_EAT_THRESHOLD:
                # Warriors with a fresh enough meal clock go (back) to the Cave.
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should never be here; send them home.
        for c in farmers:
            environment.assign_group(c, "village")

        attackers = []
        returners = []
        for c in warriors:
            # Warriors walk home to eat once their meal clock is high.
            if c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                returners.append(c)
            else:
                attackers.append(c)

        # Keep the Dragon attacked every step: if nobody is eligible,
        # keep the freshest warrior in the fight.
        if not attackers and returners:
            freshest = min(returners, key=lambda c: c.steps_since_meal)
            returners = [c for c in returners if c is not freshest]
            attackers.append(freshest)

        for c in attackers:
            environment.assign_group(c, "attack")
        for c in returners:
            environment.assign_group(c, "village")

        self._cave_attackers = len(attackers)
```