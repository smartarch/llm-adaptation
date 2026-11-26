## Analysis

Starvation is fixed, but now the Dragon never dies — the strategy became too conservative: the spawn buffer of `12 + 40` wheat was almost never reached, so the warrior population never grew, and the attack/retreat cycle (`ssm >= 3` retreat) only produced ~2 attacks per trip, which couldn't outpace the Dragon's regeneration.

Changes:

1. **Longer attack windows**: warriors in the Cave attack while `steps_since_meal <= 3` and retreat at 4 — they arrive in the Village and eat immediately (villagers eat at `ssm >= 4` in the Village), giving 3 attacks (9 damage) per 5-step cycle while still keeping a safety margin before the 6-step starvation limit.
2. **Realistic spawn thresholds**: spawn a warrior pair whenever wheat exceeds the cost plus a buffer of 20 (+ covering this step's meals), so the warrior population actually grows and sustains pressure against the Dragon's regeneration. Farmers are spawned only when the farming force drops to at most 1 (keeping the food economy alive), and farmers are converted to warriors only in the emergency case where no warriors exist at all.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)

        farmers_here = [c for c in components if c.role == "Farmer"]
        warriors_here = [c for c in components if c.role == "Warrior"]

        # Villagers that must eat this step take priority over everything else
        hungry = [c for c in components if c.steps_since_meal >= 4 or c.hp <= 1]
        meal_cost = len(hungry)

        spawn_group, spawn_pair = None, None
        if dragon_alive:
            if all_warriors or len(farmers_here) >= 4:
                # Grow the army: spawn warriors whenever we can afford it
                # with a buffer that also covers current meals.
                if len(warriors_here) >= 2 and wheat >= 12 + 20 + meal_cost:
                    spawn_group, spawn_pair = "spawn warrior", warriors_here[:2]
                elif all_warriors == [] and len(farmers_here) >= 2 \
                        and wheat >= 12 + 20 + meal_cost:
                    # Emergency: no warriors at all -> convert two farmers
                    spawn_group, spawn_pair = "spawn warrior", farmers_here[:2]
                elif len(all_farmers) <= 1 and len(farmers_here) >= 2 \
                        and wheat >= 10 + 20 + meal_cost:
                    # Keep the food economy alive
                    spawn_group, spawn_pair = "spawn farmer", farmers_here[:2]

        spawned = set(id(c) for c in (spawn_pair or []))

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_group)
            elif c.steps_since_meal >= 4 or c.hp <= 1:
                # Eat with a safety margin before the 6-step limit
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # Attack while ssm <= 3 (3 attacks per trip), then head home:
            # they arrive with ssm 5 and eat immediately in the Village,
            # still within the 6-step starvation limit.
            if c.steps_since_meal >= 4 or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```