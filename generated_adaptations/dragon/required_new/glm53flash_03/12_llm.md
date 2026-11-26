## Analysis

The Dragon kept regenerating because attack coverage had gaps: whenever no villager attacked for even one step, it healed 5 HP, wiping out roughly a warrior-attack of progress. The fix is **full-step attack coverage via phase-shifted warrior waves**:

- Each warrior gets a fixed phase `p = id % 3`. After eating, it waits `p` steps in the Village, then departs. Its attack window in the Cave is `ssm 1..3`, it returns at `ssm 4`, arrives home at `ssm 5` and eats immediately. Each warrior repeats this 6-step cycle with a fixed phase, so with ≥3 warriors (phases 0,1,2) the Dragon is attacked **every single step** — regeneration never triggers, and net damage is 3 per warrior per attack step.
- Farmers stay farming and eat at `ssm >= 3` (large margin).
- Spawning fires whenever wheat covers cost + meals + a buffer, using any two available non-hungry villagers, preferring farmers while keeping ≥2 farmers (so the food economy never collapses and the army keeps growing despite Dragon counterattacks/kills).

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)

        # Villagers that must eat this step take priority over everything else
        def hungry(c):
            if c.hp <= 1:
                return True
            return c.steps_since_meal >= (5 if c.role == "Warrior" else 3)

        hungry_set = set(id(c) for c in components if hungry(c))
        meal_cost = len(hungry_set)

        spawn_group, spawn_pair = None, None
        if dragon_alive:
            candidates = [c for c in components if id(c) not in hungry_set]
            # Spawn warriors aggressively; prefer farmers while >= 2 remain
            if wheat >= 12 + 12 + meal_cost and len(candidates) >= 2:
                farm_pool = [c for c in candidates if c.role == "Farmer"]
                if not all_warriors:
                    # Emergency: no warriors at all
                    spawn_group, spawn_pair = "spawn warrior", candidates[:2]
                elif len(all_farmers) > 2 and len(farm_pool) >= 2:
                    spawn_group, spawn_pair = "spawn warrior", farm_pool[:2]
                else:
                    spawn_group, spawn_pair = "spawn warrior", candidates[:2]
            elif len(all_farmers) <= 1 and wheat >= 10 + 12 + meal_cost:
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
                # Phase-shifted departure: after eating (ssm 0), wait
                # id % 3 steps in the Village, then depart. Waves with
                # phases 0/1/2 cover the Dragon on every step.
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
                if c.hp <= 1 or c.steps_since_meal >= 3:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
```