## Fix: cap meals at available wheat

**What failed:** The environment rejects an "eat" assignment when the farm has no wheat left for it. My village logic put every villager that needed food into "eat" without checking the wheat stock. The rejected assignment interrupted the loop, so some villagers were never assigned, which caused the "not assigned" failures.

**The fix:**
1. **Cap meals at the wheat stock.** Only as many villagers as the farm can feed go to "eat".
2. **Feed the most urgent first.** Candidates are sorted by `steps_since_meal`, highest first, so anyone close to starving is fed before anyone else.
3. **Use identity-based sets** for group membership, so every villager is assigned exactly once.
4. **Spawn only with wheat left over** after meals are paid for, as before.
5. **Keep the cave logic unchanged**, since the failing tests only involved the village phase.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors in the Cave return to the Village at this meal-clock value.
    CAVE_RETURN_THRESHOLD = 2
    # Target population used to decide what to spawn.
    MIN_FARMERS = 2
    MIN_WARRIORS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1. Collect everyone who wants a meal, then feed the most urgent
        #    first, never more villagers than the wheat stock allows.
        wants_food = []
        for c in components:
            if c.role == "Farmer":
                needs = c.steps_since_meal >= self.FARMER_EAT_THRESHOLD
            else:
                # Warriors eat whenever they are in the Village and not fresh,
                # so they can leave for the Cave with a meal clock near 0.
                needs = c.steps_since_meal >= 1
            if needs:
                wants_food.append(c)

        wants_food.sort(key=lambda c: c.steps_since_meal, reverse=True)
        eaters = wants_food[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        wheat_after_meals = wheat - len(eaters)

        non_eaters = [c for c in components if id(c) not in eater_ids]

        # 2. Choose spawning from idle (non-eating) villagers.
        spawn_group = None
        spawn_ids = set()
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]

        if len(farmers) < self.MIN_FARMERS and wheat_after_meals >= 10 and len(non_eaters) >= 2:
            spawn_group = "spawn farmer"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_ids = {id(c) for c in pool[:2]}
        elif len(warriors) < self.MIN_WARRIORS and wheat_after_meals >= 12 and len(non_eaters) >= 2:
            spawn_group = "spawn warrior"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_ids = {id(c) for c in pool[:2]}

        # 3. Assign every villager to exactly one group.
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif spawn_group is not None and cid in spawn_ids:
                environment.assign_group(c, spawn_group)
            elif c.role == "Warrior" and c.steps_since_meal == 0:
                # Fresh warriors go to the Cave to attack.
                environment.assign_group(c, "cave")
            else:
                # Farmers (and any warrior not yet ready) keep farming.
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
            # Hungry warriors go home to eat before they starve.
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
```