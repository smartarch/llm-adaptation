

Looking at the seed=3 failure, the core problem is that dragon counter-attacks kill warriors faster than they're replaced, causing attack gaps where the dragon regens 5 HP/step. I need to:

1. **Spawn warriors every possible step** using any available villagers as parents (they aren't consumed, just skip that step)
2. **Deploy more aggressively** - warriors go to cave even with s_m=2-3 when attackers are few
3. **Last push mode** - when dragon HP is low, nobody retreats to eat
4. **Sacrifice farming** when warrior count is critically low to send farmers to prevent regen
5. **Lower wheat thresholds** for spawning to build the army faster

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_w = list(environment.warriors)
        all_f = list(environment.farmers)
        num_w = len(all_w)
        num_f = len(all_f)
        total = num_w + num_f
        dragon_hp = environment.dragon.hp

        # Count villagers currently in cave (potential attackers)
        cave_count = sum(1 for v in all_w + all_f if v.location == "Cave")

        # 1) Villagers that must eat NOW (s_m >= 4 to avoid HP loss)
        eat_set = set()
        for c in components:
            if c.steps_since_meal >= 4 and dragon_hp > 12:
                environment.assign_group(c, "eat")
                eat_set.add(id(c))

        remaining = [c for c in components if id(c) not in eat_set]
        v_f = [c for c in remaining if c.role == "Farmer"]
        v_w = [c for c in remaining if c.role == "Warrior"]

        # 2) Aggressive warrior spawning every step if possible
        spawn_ids = set()
        reserve = max(total, 5)  # wheat to feed everyone once

        # Build pool of 2 potential spawn parents, preferring farmers
        # Keep at least 1 farmer farming for wheat income
        min_farm = 1 if len(v_f) >= 1 else 0
        parent_pool = list(v_f[min_farm:]) + list(v_w)

        spawned_warrior = False
        if wheat >= 12 + reserve and len(parent_pool) >= 2:
            environment.assign_group(parent_pool[0], "spawn warrior")
            environment.assign_group(parent_pool[1], "spawn warrior")
            spawn_ids = {id(parent_pool[0]), id(parent_pool[1])}
            spawned_warrior = True
        elif wheat >= 12 and len(parent_pool) >= 2:
            # Lower threshold when desperate for warriors
            environment.assign_group(parent_pool[0], "spawn warrior")
            environment.assign_group(parent_pool[1], "spawn warrior")
            spawn_ids = {id(parent_pool[0]), id(parent_pool[1])}
            spawned_warrior = True

        if not spawned_warrior and num_f < 2 and wheat >= 10 + reserve and len(v_f) >= 2:
            environment.assign_group(v_f[0], "spawn farmer")
            environment.assign_group(v_f[1], "spawn farmer")
            spawn_ids = {id(v_f[0]), id(v_f[1])}

        v_f = [c for c in v_f if id(c) not in spawn_ids]
        v_w = [c for c in v_w if id(c) not in spawn_ids]

        # 3) Assign farmers: farm or emergency attack
        # Keep 1-2 farming, send rest to cave if attack coverage low
        farm_count = min(2, len(v_f)) if num_w >= 2 else min(1, len(v_f))

        for i, c in enumerate(v_f):
            if i < farm_count:
                environment.assign_group(c, "farm")
            elif dragon_hp <= 12:
                # Last push: everyone attacks
                environment.assign_group(c, "cave")
            elif cave_count < 2 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # 4) Warriors: send to cave aggressively
        for c in v_w:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            elif dragon_hp <= 12:
                # Last push
                environment.assign_group(c, "cave")
            elif c.steps_since_meal <= 3 and cave_count < 3:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            if c.steps_since_meal >= 4 and dragon_hp > 12:
                # Retreat to eat only if dragon isn't nearly dead
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```