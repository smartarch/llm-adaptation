

Looking at the failures, the core issue is that villagers in the **Cave** with `steps_since_meal >= 4` must leave immediately (since traveling takes 1 step, arriving at ssm=5 means they can eat that step, but arriving at ssm=6 means they starve). My code was using `>= 5` as the threshold.

Additionally, I need to handle the village eat/farm priority more carefully:
- `ssm >= 4` in village: MUST eat (farm only if wheat=0)
- `ssm == 3` warriors: eat to reset for a fresh cave cycle
- Fresh warriors (ssm ≤ 2): go to cave
- Farmers: spawn warriors or farm

The cycle works: eat(ssm=3→0) → travel(ssm=1) → attack(ssm=2) → attack(ssm=3) → attack(ssm=4) → travel back(ssm=5) → eat(ssm=6→0). Wait, ssm=6 would starve... Let me recalculate: eat at ssm=3 resets to 0. Travel to cave: ssm=1. Attack x3: ssm=2,3,4. Leave cave at ssm=4: travel to village, ssm=5. Eat at ssm=5: resets. This is safe.

```py
import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat_remaining = environment.farm.wheat

        # Categorize by urgency of eating need
        ssm4_plus = [c for c in components if c.steps_since_meal >= 4]
        ssm3_warriors = [c for c in components if c.steps_since_meal == 3 and c.role == "Warrior"]
        ssm3_farmers = [c for c in components if c.steps_since_meal == 3 and c.role == "Farmer"]
        fresh = [c for c in components if c.steps_since_meal <= 2]

        # Priority 1: ssm >= 4 MUST eat now (farm only if no wheat at all)
        for c in ssm4_plus:
            if wheat_remaining >= 1:
                environment.assign_group(c, "eat")
                wheat_remaining -= 1
            else:
                # No wheat available — farm to produce, will eat next step
                environment.assign_group(c, "farm")

        # Priority 2: warriors at ssm=3 eat to reset for a fresh 3-attack cycle
        for c in ssm3_warriors:
            if wheat_remaining >= 1:
                environment.assign_group(c, "eat")
                wheat_remaining -= 1
            else:
                environment.assign_group(c, "farm")

        # Priority 3: farmers at ssm=3 eat to keep food cycle regular
        for c in ssm3_farmers:
            if wheat_remaining >= 1:
                environment.assign_group(c, "eat")
                wheat_remaining -= 1
            else:
                environment.assign_group(c, "farm")

        # Priority 4: fresh warriors go to cave
        fresh_warriors = [c for c in fresh if c.role == "Warrior"]
        for w in fresh_warriors:
            environment.assign_group(w, "cave")

        # Priority 5: fresh farmers — spawn warriors or farm
        fresh_farmers = [c for c in fresh if c.role == "Farmer"]
        total_warriors_now = len(environment.warriors)
        total_villagers = len(environment.warriors) + len(environment.farmers)

        # Estimate upcoming meal costs over next ~3 steps
        # Each villager eats roughly once every 6 steps → ~total/2 over 3 steps
        # Be conservative: reserve enough so we don't run out
        upcoming_meals_needed = 0
        for v in environment.warriors + environment.farmers:
            if v.location == "Cave" and v.steps_since_meal >= 3:
                upcoming_meals_needed += 1  # will arrive in village soon, need to eat
            elif v.location == "Village" and v.steps_since_meal >= 3 and v not in components:
                upcoming_meals_needed += 1

        # Farming this step will produce wheat, so we have more next step
        # For spawning NOW, we need wheat from current reserve
        spawn_count = 0
        if len(fresh_farmers) >= 2:
            if total_warriors_now == 0 and wheat_remaining >= 12:
                # Critical: no warriors at all, spawn one ASAP
                spawn_count = 1
            elif total_warriors_now < 6 and wheat_remaining >= 12 + upcoming_meals_needed:
                # Grow warrior army
                spawn_count = 1
            elif total_villagers < 5 and wheat_remaining >= 10 + upcoming_meals_needed:
                # Need more total villagers
                spawn_count = 1

        idx = 0
        for _ in range(spawn_count):
            if idx + 1 < len(fresh_farmers):
                environment.assign_group(fresh_farmers[idx], "spawn warrior")
                environment.assign_group(fresh_farmers[idx + 1], "spawn warrior")
                idx += 2

        # Remaining fresh farmers always farm
        for i in range(idx, len(fresh_farmers)):
            environment.assign_group(fresh_farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Must leave NOW: travel 1 step → arrive at ssm=5 → can eat that step
                # If we wait until ssm=5: travel → arrive at ssm=6 → STARVES
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                # Too fragile, retreat
                environment.assign_group(c, "village")
            else:
                # Attack the dragon every step
                environment.assign_group(c, "attack")
```