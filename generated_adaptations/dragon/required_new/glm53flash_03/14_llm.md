## Analysis

The starvations (Mark, William, Donald — all eating at safe thresholds) reveal the true root cause: **wheat shortages**. Villagers were assigned to "eat" but the meal couldn't be paid for, because my aggressive spawning kept converting farmers into warriors and draining the granary. Once wheat hit zero, everyone starved regardless of thresholds.

Fixes:

1. **Economy-first spawning**: never spawn unless wheat covers the cost *plus* a reserve of `4 × population` wheat (several steps of meals for the whole colony). Pause all spawning when wheat is low. Keep at least 2 dedicated farmers at all times (3 in larger colonies) — farmers are only consumed by spawning above that floor.
2. **Safety margins everywhere**: warriors eat at `ssm >= 4` in the Village; in the Cave they attack at `ssm 1–3` and return at 4 (arriving home at 5, still fed in time). Farmers eat at `ssm >= 3`.
3. **Continuous attack coverage** via phase-shifted departures (`id % 3`): after eating, a warrior waits that many steps before departing, so with ≥3 warriors the Dragon is attacked every step and its regeneration never kicks in.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)
        total_pop = len(all_warriors) + len(all_farmers)

        # Villagers that must eat this step take priority over everything else
        def hungry(c):
            if c.hp <= 1:
                return True
            return c.steps_since_meal >= (4 if c.role == "Warrior" else 3)

        hungry_set = set(id(c) for c in components if hungry(c))
        meal_cost = len(hungry_set)

        # Reserve wheat for several steps of meals for the whole colony
        reserve = 4 * total_pop + 5
        spawn_group, spawn_pair = None, None
        if dragon_alive:
            candidates = [c for c in components if id(c) not in hungry_set]
            min_farmers = 3 if total_pop >= 6 else 2
            farmers_after = len(all_farmers)
            # Emergency: no warriors at all -> must create some
            if not all_warriors and len(candidates) >= 2 \
                    and wheat >= 12 + reserve + meal_cost:
                spawn_group, spawn_pair = "spawn warrior", candidates[:2]
            # Regular warrior growth, only from surplus wheat and
            # only if enough farmers remain to sustain the food economy
            elif len(candidates) >= 2 and wheat >= 12 + reserve + meal_cost \
                    and farmers_after - 2 >= min_farmers:
                pool = [c for c in candidates if c.role == "Farmer"]
                if len(pool) >= 2:
                    spawn_group, spawn_pair = "spawn warrior", pool[:2]
                else:
                    spawn_group, spawn_pair = "spawn warrior", candidates[:2]
            # Rebuild the farming base if it collapsed
            elif len(all_farmers) < min_farmers and len(candidates) >= 2 \
                    and wheat >= 10 + reserve + meal_cost:
                pool = [c for c in candidates if c.role == "Farmer"]
                if len(pool) >= 2:
                    spawn_group, spawn_pair = "spawn farmer", pool[:2]

        spawned = set(id(c) for c in (spawn_pair or []))

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_group)
            elif id(c) in hungry_set:
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                # Phase-shifted departure (id % 3): with >=3 warriors the
                # Dragon is attacked every step -> no regeneration.
                phase = id(c) % 3
                if c.steps_since_meal >= 1 + phase:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # 3 attacks (ssm 1..3), return at ssm 4, arrive home at
                # ssm 5 and eat immediately -> never reaches 6.
                if c.hp <= 1 or c.steps_since_meal >= 4:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            else:
                if c.hp <= 1 or c.steps_since_meal >= 2:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
```