The bug: `assign_group` expects the group **name** (as in `group_ids`), not an index — I was passing integer indices, causing invalid assignments and thus nobody acting (leading to starvation and loss). I'll pass names directly, ensure every component is assigned exactly once, and tighten the spawning logic (spawn warriors early when wheat allows, prefer spawning warriors when none exist).

```py
import generated_adaptations.base_classes.dragon as base


class SmartAdaptation(base.DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        villagers = list(components)

        # hungriest first; warriors before farmers
        villagers.sort(key=lambda c: (c.steps_since_meal, 0 if c.role == "Warrior" else 1))

        assigned = set()

        # 1) eat: anyone about to starve (starving starts after 6 steps)
        for c in villagers:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        remaining = [c for c in villagers if id(c) not in assigned]
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        total = len(environment.farmers) + len(environment.warriors)
        warrior_count = len(environment.warriors)
        meal_reserve = total + 2  # keep a reserve of meals

        # 2) spawning
        spawn = None
        # priority: if no warriors at all, spawn warriors with any two healthy villagers
        if warrior_count == 0 and wheat >= 12 + meal_reserve and len(remaining) >= 2:
            spawn = ("spawn warrior", remaining[:2])
        elif wheat >= 12 + meal_reserve and len(remaining) >= 2:
            # prefer spawning warriors from villagers (farmers if no warriors available)
            pool = warriors if len(warriors) >= 2 else farmers
            if len(pool) >= 2:
                spawn = ("spawn warrior", pool[:2])
        elif wheat >= 10 + meal_reserve and total < 5 and len(farmers) >= 2:
            spawn = ("spawn farmer", farmers[:2])

        if spawn:
            name, pair = spawn
            for c in pair:
                environment.assign_group(c, name)
                assigned.add(id(c))

        # 3) everyone else: warriors go to the Cave, farmers farm
        for c in remaining:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")
            assigned.add(id(c))

        # safety: make sure every component got exactly one assignment
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 3:
                # return in time: travel (1) + eat (1) keeps us under the 6-step limit
                environment.assign_group(c, "village")
            elif c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # farmers are weak attackers; send them home to farm
                environment.assign_group(c, "village")
```

Key fixes:
1. **Group names instead of indices** — `assign_group` now receives `"eat"`, `"farm"`, `"cave"`, etc., matching the required group IDs exactly. This was the root cause of nearly all failures.
2. **Guaranteed full assignment** — a final safety loop ensures every component is assigned exactly once.
3. **Spawning priority** — if there are no warriors anywhere, spawn warriors immediately when wheat allows (fixing the "no warriors" optional constraint), with a meal reserve so nobody starves.