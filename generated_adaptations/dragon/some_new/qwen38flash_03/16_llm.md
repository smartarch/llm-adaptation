

Looking at the failures, the core problems are:

1. **Not reserving wheat for future meals** — The test checks that after all eating, spawning, and farming, there's enough wheat for villagers who will need to eat NEXT step (s_m will be >= 5).
2. **Dragon not killed for seeds 1 and 3** — Need more aggressive warrior deployment and fewer attack gaps.
3. **no_initial_warriors** — Must spawn warriors as soon as wheat >= 12.

The fix: After assigning eaters, compute how many villagers will have `s_m >= 5` next step (they MUST eat). Only allow spawning if `wheat_remaining - spawn_cost + farm_income >= meals_due_next_step`.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_villagers = list(environment.warriors) + list(environment.farmers)
        num_w = len(environment.warriors)

        # --- PHASE 1: Mandatory eating (s_m >= 4 → must eat or starve soon) ---
        eaters = [c for c in components if c.steps_since_meal >= 4]
        # Sort most urgent first
        eaters.sort(key=lambda c: c.steps_since_meal, reverse=True)
        eat_set = set()
        wheat_after_eat = wheat
        for c in eaters:
            if wheat_after_eat >= 1:
                environment.assign_group(c, "eat")
                wheat_after_eat -= 1
                eat_set.add(id(c))
            # If no wheat, they can't eat (will starve – we must avoid this)

        # --- PHASE 2: Compute meals needed next step for reservation ---
        # A villager needs to eat next step if their s_m_next >= 5
        # (meaning they have exactly 1 step before starvation at s_m=6)
        meals_next_step = 0
        for v in all_villagers:
            if v.location == "Village":
                if id(v) in eat_set:
                    pass  # s_m resets to 0, fine
                else:
                    # s_m increases by 1 next step
                    if v.steps_since_meal >= 4:
                        meals_next_step += 1
            elif v.location == "Cave":
                # If in cave and s_m >= 3, they'll go to village
                # arrive with s_m+1. If s_m >= 4, arrive at s_m=5 → must eat
                # If s_m == 3, go to village, arrive s_m=4, next step s_m=5
                if v.steps_since_meal >= 4:
                    meals_next_step += 1
            # Note: v.location might not be perfectly accurate for
            # villagers just assigned, but we use it for reservation

        # --- PHASE 3: Estimate farm income this step ---
        # We'll count this after assigning farmers, but estimate now
        # Conservatively assume 1 farmer farming = 5 income
        # We'll refine: non-eating villagers not spawned = will farm or go cave

        non_eat = [c for c in components if id(c) not in eat_set]
        non_eat.sort(key=lambda c: 0 if c.role == "Farmer" else 1)

        # --- PHASE 4: Spawning (only if wheat allows) ---
        spawn_set = set()
        # Estimate farm income: assume remaining farmers (up to 2) will farm
        est_farm_income = 0
        farmers_avail = [c for c in non_eat if c.role == "Farmer" and id(c) not in spawn_set]
        warriors_avail = [c for c in non_eat if c.role == "Warrior" and id(c) not in spawn_set]

        # Try spawning warrior with 2 villagers as parents
        # Parents are NOT consumed, they just skip this step
        spawn_parent_candidates = non_eat  # any non-eating villager can be a parent

        if wheat_after_eat >= 12 and len(spawn_parent_candidates) >= 2:
            # Check: after spawn, wheat + farm_income >= meals_next_step?
            # Farm income from remaining farmers (minus 2 used as parents)
            remaining_farmers_for_farming = len(
                [c for c in spawn_parent_candidates[2:] if c.role == "Farmer"]
            )
            # Also warriors farming produce 2 each, but most go to cave
            est_income = 5 * min(remaining_farmers_for_farming, 2)
            if wheat_after_eat - 12 + est_income >= meals_next_step:
                environment.assign_group(spawn_parent_candidates[0], "spawn warrior")
                environment.assign_group(spawn_parent_candidates[1], "spawn warrior")
                spawn_set = {id(spawn_parent_candidates[0]), id(spawn_parent_candidates[1])}
                wheat_after_eat -= 12

        # --- PHASE 5: Assign remaining villagers ---
        remaining = [c for c in components if id(c) not in eat_set and id(c) not in spawn_set]

        # Keep at least 1 farmer farming for wheat production
        farmers_remaining = [c for c in remaining if c.role == "Farmer"]
        warriors_remaining = [c for c in remaining if c.role == "Warrior"]

        for i, c in enumerate(farmers_remaining):
            if i == 0:
                environment.assign_group(c, "farm")
            elif i == 1 and len(farmers_remaining) > 2:
                # Second farmer: farm for wheat, or go cave if warriors scarce
                if num_w <= 1 and c.steps_since_meal <= 2:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
            elif num_w <= 1 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        for c in warriors_remaining:
            if c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            elif num_w <= 1 and c.steps_since_meal <= 3:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # MUST go to village now (travel=1 step, arrive s_m=5, eat s_m=0)
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```