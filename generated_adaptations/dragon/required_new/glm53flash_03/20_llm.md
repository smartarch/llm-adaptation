## Analysis

The bottleneck: the army never grows. My reserve of `4×pop + 5 ≈ 25+` wheat meant spawning almost never fired, while the Dragon's counterattacks attrited the starting warriors. With a shrinking 2–3 warriors, damage cannot outpace regeneration within 30 steps — aggressive spawning is mandatory.

Fixes:
1. **Small spawn buffer** (cost + 10 + current meals): spawn whenever affordable.
2. **Prefer spawning from warrior pairs** — consumes no farmers, keeps the food economy intact.
3. **Keep the proven schedule** (the one that won 67% earlier): eat in the Village at `ssm ≥ 3`, in the Cave attack while `ssm ≤ 3`, return at `ssm ≥ 4`. Different warriors' cycles drift into different phases, giving near-continuous Dragon coverage so regeneration rarely triggers.

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

        spawn_group, spawn_pair = None, None
        if dragon_alive:
            candidates = [c for c in components if id(c) not in hungry_ids]
            warrior_pool = [c for c in candidates if c.role == "Warrior"]
            farm_pool = [c for c in candidates if c.role == "Farmer"]

            if not all_warriors:
                # Emergency: no warriors at all -> must create some
                if len(candidates) >= 2 and wheat >= 12 + 10 + meal_cost:
                    spawn_group, spawn_pair = "spawn warrior", candidates[:2]
            elif len(warrior_pool) >= 2 and wheat >= 12 + 10 + meal_cost:
                # Prefer spawning from warrior pairs: consumes no farmers,
                # keeps the food economy fully intact while the army grows.
                spawn_group, spawn_pair = "spawn warrior", warrior_pool[:2]
            elif len(farm_pool) >= 2 and len(all_farmers) >= 4 \
                    and wheat >= 12 + 10 + meal_cost:
                # Otherwise convert surplus farmers, keeping >= 2 farmers
                spawn_group, spawn_pair = "spawn warrior", farm_pool[:2]
            elif len(all_farmers) < 2 and len(candidates) >= 2 \
                    and wheat >= 10 + 10 + meal_cost:
                # Rebuild the farming base if it collapsed
                pair = farm_pool[:1] + [c for c in warrior_pool
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
            # Attack while ssm <= 3 (3 attacks per trip), then head home:
            # they arrive in the Village with ssm 5 and eat immediately,
            # well within the 6-step starvation limit.
            if c.hp <= 1 or c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```