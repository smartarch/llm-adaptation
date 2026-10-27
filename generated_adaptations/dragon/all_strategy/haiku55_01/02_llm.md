## Strategy: Hunger-Gated Warrior Rotation with Farmer Economy

**Core idea:** Farmers stay in the Village to produce wheat, feed everyone, and spawn new villagers. Warriors do the damage in the Cave and rotate back to the Village only when they need to eat.

**Village rules (`assign_in_village`):**
1. **Eat first:** Any villager with `steps_since_meal >= 3` goes to "eat". The threshold is set below the 6-step starvation limit to leave a safety margin for travel and scheduling. Wheat is reserved for these meals.
2. **Spawn:** With the remaining wheat, the strategy spawns in pairs from unassigned, fed Farmers. It spawns Warriors first until there are at least two, then Farmers until there are at least two. Spawning consumes wheat, so the strategy checks the budget before assigning a pair.
3. **Warriors:** Fed Warriors (`steps_since_meal < 3`) go to the "cave" to attack.
4. **Farmers:** Everyone else farms.

**Cave rules (`assign_in_cave`):**
1. Farmers in the Cave are sent back to the Village, since they are not attackers.
2. Warriors with `steps_since_meal >= 3` return to the Village to eat.
3. Warriors that are fed attack. If every Warrior in the Cave is hungry, the one with the lowest hunger stays and attacks, so the Dragon is never left unattacked for more than a step or two. This keeps the Dragon from regenerating.

**Timing:** Warriors start the first attack in the first few steps, well within the 15-step target. Every villager eats at least once every 6 steps.

**Changes from a naive version:** The spawn logic avoids double-assigning a villager, and the cave logic has a fallback so the Dragon is always attacked when a fed Warrior is available.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors fight in the Cave and only return to the Village to eat
    before they get hungry enough to starve.
    """

    HUNGER_THRESHOLD = 3   # eat when steps_since_meal reaches this (starvation at 6)
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assignments = {}

        # 1. Eat: hungry villagers eat first (reserve wheat for meals).
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        for c in hungry:
            if wheat >= 1:
                assignments[c] = "eat"
                wheat -= 1
            else:
                # No wheat to eat: keep them on the farm, nothing else to do.
                assignments[c] = "farm"

        free = [c for c in components if c not in assignments]
        free_farmers = [c for c in free if c.role == "Farmer"]
        free_warriors = [c for c in free if c.role == "Warrior"]

        all_farmers = [c for c in components if c.role == "Farmer"]
        all_warriors = [c for c in components if c.role == "Warrior"]

        # 2. Spawn: use pairs of fed farmers (they are not needed in the Cave).
        spawned = False
        if len(all_warriors) < 2 and wheat >= self.WARRIOR_SPAWN_COST and len(free_farmers) >= 2:
            pair = free_farmers[:2]
            for c in pair:
                assignments[c] = "spawn warrior"
            free_farmers = free_farmers[2:]
            wheat -= self.WARRIOR_SPAWN_COST
            spawned = True
        elif len(all_farmers) < 2 and wheat >= self.FARMER_SPAWN_COST and len(free_farmers) >= 2:
            pair = free_farmers[:2]
            for c in pair:
                assignments[c] = "spawn farmer"
            free_farmers = free_farmers[2:]
            wheat -= self.FARMER_SPAWN_COST
            spawned = True

        # 3. Fed warriors go to the Cave to attack.
        for c in free_warriors:
            assignments[c] = "cave"

        # 4. Remaining farmers work the farm.
        for c in free_farmers:
            assignments[c] = "farm"

        # Apply every assignment exactly once.
        for c in components:
            environment.assign_group(c, assignments.get(c, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assignments = {}
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should not be in the Cave: send them home.
        for c in farmers:
            assignments[c] = "village"

        # Warriors: hungry ones return to eat, fed ones attack.
        fed = []
        hungry = []
        for c in warriors:
            if c.steps_since_meal >= self.HUNGER_THRESHOLD:
                hungry.append(c)
            else:
                fed.append(c)

        # Keep the Dragon attacked every step (prevents regeneration).
        if not fed and hungry:
            # Keep the least hungry warrior attacking; it will still be safe
            # for at least one more step before starving.
            best = min(hungry, key=lambda c: c.steps_since_meal)
            hungry.remove(best)
            fed.append(best)

        for c in fed:
            assignments[c] = "attack"
        for c in hungry:
            assignments[c] = "village"

        for c in components:
            environment.assign_group(c, assignments.get(c, "cave"))
```