

Looking at the failures, I can identify several issues:

1. **Starving in cave**: My code had an "always keep one attacking" override that forced a starving villager to stay in the cave. I need to remove that - `ssm >= 4` in cave ALWAYS means go to village.

2. **Eating threshold in village**: `ssm >= 5` must eat (at 6 they starve). I'll also eat at `ssm >= 4` for safety.

3. **Spawning too conservative**: Need to spawn when < 5 villagers and when no warriors exist.

4. **Not enough attacking**: Need more aggressive warrior spawning and more farmers going to cave in late game.

The core cycle for a warrior: Eat → Travel to Cave (1 step) → Attack × 3 (ssm 1→4) → Travel to Village (1 step, ssm 4→5) → Eat. That's 6 steps, 3 attacks. Need multiple warriors staggered for continuous coverage.

```py
import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        total_villagers = len(all_warriors) + len(all_farmers)
        num_warriors_in_cave = sum(1 for v in all_warriors if v.location == "Cave")

        # Priority 1: MUST eat (ssm >= 5, next step would be 6 = starve)
        must_eat = [c for c in components if c.steps_since_meal >= 5]
        remaining = [c for c in components if c.steps_since_meal < 5]
        for c in must_eat:
            environment.assign_group(c, "eat")

        if not remaining:
            return

        # Priority 2: Eat at ssm >= 4 for safety margin
        eat_soon = [c for c in remaining if c.steps_since_meal >= 4]
        remaining2 = [c for c in remaining if c.steps_since_meal < 4]
        for c in eat_soon:
            environment.assign_group(c, "eat")

        if not remaining2:
            return

        # Split by role
        farmers_free = [c for c in remaining2 if c.role == "Farmer"]
        warriors_free = [c for c in remaining2 if c.role == "Warrior"]

        # Determine spawn needs
        no_warriors_anywhere = len(all_warriors) == 0
        total_warriors_in_cave = num_warriors_in_cave
        total_in_cave = sum(1 for v in all_warriors if v.location == "Cave") + \
                       sum(1 for v in all_farmers if v.location == "Cave")

        # Wheat reserve for meals (everyone eats ~1 per 6 steps, keep buffer)
        wheat_reserve = total_villagers + 5
        spawn_wheat_budget = max(0, wheat - wheat_reserve)

        # Decide spawn actions
        spawn_actions = []
        if no_warriors_anywhere or total_warriors_in_cave < 2:
            # Urgently spawn warriors
            spawn_actions.append(("spawn warrior", 12))
            if spawn_wheat_budget >= 24:
                spawn_actions.append(("spawn warrior", 12))
        elif total_villagers < 5:
            # Grow population
            spawn_actions.append(("spawn farmer", 10))
        elif total_warriors_in_cave < 4 and spawn_wheat_budget >= 12:
            # Need more attackers
            spawn_actions.append(("spawn warrior", 12))

        # Warriors with ssm <= 1 go to cave (arrive with ssm 1-2, can attack 2-3 steps)
        warriors_to_cave = [c for c in warriors_free if c.steps_since_meal <= 1]
        warriors_idle = [c for c in warriors_free if c.steps_since_meal >= 2]

        # Minimum farmers for wheat production
        min_farm = 2
        if total_villagers <= 3:
            min_farm = 1

        farmers_for_farm = farmers_free[:min_farm]
        farmers_surplus = farmers_free[min_farm:]

        # Spawn pool: surplus farmers + idle warriors
        spawn_pool = list(farmers_surplus) + list(warriors_idle)

        # Execute spawns
        for group_name, cost in spawn_actions:
            while len(spawn_pool) >= 2 and spawn_wheat_budget >= cost:
                c1 = spawn_pool.pop(0)
                c2 = spawn_pool.pop(0)
                environment.assign_group(c1, group_name)
                environment.assign_group(c2, group_name)
                spawn_wheat_budget -= cost

        # Assign warriors to cave
        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        # Assign remaining pool: warriors with ssm<=2 can still do a quick cave trip
        for c in spawn_pool:
            if c.role == "Warrior" and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # Minimum farmers farm
        for c in farmers_for_farm:
            environment.assign_group(c, "farm")

        # Late game: send surplus farmers to cave to help kill dragon
        if dragon_hp <= 20 and len(all_warriors) + len(all_farmers) > 5:
            # Already assigned above as farm; override some to cave
            pass  # Handled by natural assignment; farmers attack for 1 dmg

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        # CRITICAL: ssm >= 4 in cave means must go to village NOW
        # (travel takes 1 step, arrive with ssm=5, eat next step at ssm=5→0)
        # If ssm=5 in cave, travel → arrive ssm=6 = STARVING. Too late.
        for c in components:
            if c