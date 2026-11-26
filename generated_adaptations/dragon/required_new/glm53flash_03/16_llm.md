## Analysis

Comparing with the earlier runs: the **first version** (eat at `ssm ≥ 3`, attack in Cave while `ssm ≤ 3`, return at `ssm ≥ 4`) actually won 67% of games — its schedule is proven. It failed only because its spawn rules drained farmers (economy collapse → starvation). Later versions broke the schedule itself (later eating, earlier retreat → fewer attacks; huge spawn buffers → army never grew), which killed the win rate entirely.

So the fix: **restore the proven schedule exactly**, and make spawning both *reliable* (any two available villagers, not "two warriors in the Village") and *economy-safe* (always keep ≥2 farmers, keep a wheat reserve covering upcoming meals, emergency conversion only when no warriors exist). Optionally, pair a lone farmer with a warrior to rebuild the farmer base.

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
        hungry = [c for c in components if c.hp <= 1 or c.steps_since_meal >= 3]
        hungry_ids = set(id(c) for c in hungry)
        meal_cost = len(hungry)

        # Reserve: meals for the whole colony for the next ~4 steps
        reserve = 4 * total_pop + 5

        spawn_group, spawn_pair = None, None
        if dragon_alive:
            candidates = [c for c in components if id(c) not in hungry_ids]
            farm_pool = [c for c in candidates if c.role == "Farmer"]
            warriors_here = [c for c in candidates if c.role == "Warrior"]

            if not all_warriors:
                # Emergency: no warriors at all -> must create some
                if len(candidates) >= 2 and wheat >= 12 + reserve + meal_cost:
                    spawn_group, spawn_pair = "spawn warrior", candidates[:2]
            elif len(farm_pool) >= 2 and len(all_farmers) - 2 >= 2 \
                    and wheat >= 12 + reserve + meal_cost:
                # Grow the army from surplus farmers, keeping >= 2 farmers
                spawn_group, spawn_pair = "spawn warrior", farm_pool[:2]
            elif len(all_farmers) < 2 and len(farm_pool) + len(warriors_here) >= 2 \
                    and wheat >= 10 + reserve + meal_cost:
                # Rebuild the farming base (may pair a farmer with a warrior)
                pair = farm_pool[:1] + [c for c in warriors_here
                                        if c not in farm_pool][:1]
                if len(pair) < 2:
                    pair = candidates[:2]
                if len(pair) >= 2:
                    spawn_group, spawn_pair = "spawn farmer", pair[:2]

        spawned = set(id(c) for c in (spawn_pair or []))

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_group)
            elif id(c) in hungry_ids:
                # Eat with a safety margin before the 6-step starvation limit
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                # Healthy, fed warriors head out to attack the Dragon
                environment.assign_group(c, "cave")
            else:
                # Farmers keep the food economy running
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # Attack while ssm <= 3 (2 attacks per trip), then head home:
            # they arrive in the Village with ssm 5 and eat immediately,
            # well within the 6-step starvation limit.
            if c.hp <= 1 or c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```