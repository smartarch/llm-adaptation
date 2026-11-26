

Looking at the failures, the dragon isn't being killed because the strategy is too conservative with sending warriors and spawning. The previous successful version had a 100% win rate but failed constraints. I need to combine aggressive attacking with proper wheat budgeting.

Key analysis:
- Dragon needs 100 HP damage in <30 steps → need ~4+ damage/step average
- Warriors deal 3 damage → need ~2 warriors attacking every step with zero gaps
- Each warrior can only attack 3 consecutive steps before needing to return+eat (6 step cycle)
- Need 4-6 warriors cycling at any time
- Must spawn warriors aggressively (12 wheat each) while maintaining food for all villagers
- Wheat reservation must account for cave warriors returning soon

The previous bug was that spawn thresholds were too strict (reserving too much wheat), leaving cave undermanned. Also, sending was limited to 2/step, creating gaps.

New approach:
- Target 4 attackers in cave always (6 when desperate)
- Send up to 3 warriors per step when cave is undermanned
- Simpler wheat budget: check current wheat covers current meals + 12 buffer for spawn
- Always eat meal≥4 villagers in village (mandatory)
- Always return cave villagers at meal≥4 (mandatory)
- Spawn as soon as we have 12+ wheat after mandatory meals

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        assigned = set()
        meals_this_step = 0

        # PRIORITY 1: Mandatory eat - villagers at meal >= 4 must eat now
        # (if at 5, they starve next step; at 4, safe one more but eat now is best)
        # Sort most urgent first
        urgent = sorted(
            [c for c in components if c.steps_since_meal >= 4],
            key=lambda c: -c.steps_since_meal
        )
        for c in urgent:
            if meals_this_step < wheat:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                meals_this_step += 1
            # else: no wheat, will starve - assign to farm (cannot eat)

        # PRIORITY 2: Send warriors to cave to maintain attack rotation
        cave_warriors = sum(1 for v in environment.warriors if v.location == "Cave")
        cave_farmers = sum(1 for v in environment.farmers if v.location == "Cave")
        num_cave = cave_warriors + cave_farmers

        # Attack target: need continuous coverage
        if dragon_hp <= 20:
            target = 6
        elif dragon_hp <= 50:
            target = 5
        else:
            target = 4

        need = max(0, target - num_cave)

        # Best candidates: warriors with low meal and good HP
        remaining = [c for c in components if id(c) not in assigned]
        warriors_sorted = sorted(
            [c for c in remaining if c.role == "Warrior" and c.steps_since_meal <= 2 and c.hp >= 2],
            key=lambda c: c.steps_since_meal
        )

        # Send up to need, batch-limited (3 at once if cave empty, 2 otherwise)
        batch = 3 if num_cave <= 1 else 2
        sent = 0
        for w in warriors_sorted:
            if sent >= need or sent >= batch:
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sent += 1

        # Desperate: still need attackers, send anyone OK
        if num_cave == 0 and sent < need:
            backup = sorted(
                [c for c in components if id(c) not in assigned and c.steps_since_meal <= 3 and c.hp >= 2],
                key=lambda c: (c.role != "Warrior", c.steps_since_meal)
            )
            for c in backup:
                if sent >= need:
                    break
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                sent += 1

        # PRIORITY 3: Spawn warriors when affordable
        # Need: 12 wheat AND 2 free villagers
        # Reserve enough for meals this step already handled
        # Check future food needs: villagers in cave with high meal will return and need to eat
        wheat_left = wheat - meals_this_step
        # Conservative reserve: number of villagers currently at meal >= 3 anywhere (will need meals soon)
        total_villagers = len(environment.warriors) + len(environment.farmers)
        future_meal_demand = sum(
            1 for v in list(environment.warriors) + list(environment.farmers)
            if v.steps_since_meal >= 3
        )
        # We can spawn if wheat_left covers spawn + a buffer
        # farming this step will produce more wheat, so be moderately aggressive
        remaining_now = [c for c in components if id(c) not in assigned]
        farm_estimate = sum(5 if c.role == "Farmer" else 2 for c in remaining_now if c.steps_since_meal < 3)
        projected_wheat = wheat_left + farm_estimate

        can_spawn = (
            projected_wheat >= 12 + max(0, future_meal_demand - meals_this_step) + 5
            and len(remaining_now) >= 4
            and total_villagers < 12  # cap population to manage food
        )

        if can_spawn:
            # Prefer farmers for spawn (preserve warriors for attack)
            farmers_avail = [c for c in remaining_now if c.role == "Farmer"]
            others_avail = [c for c in remaining_now if c.role != "Farmer"]
            pool = (farmers_avail + others_avail)[:2]
            if len(pool) >= 2:
                for s in pool:
                    environment.assign_group(s, "spawn warrior")
                    assigned.add(id(s))

        # PRIORITY 4: Optional eat at meal 3 to smooth future demand (only if wheat surplus)
        wheat_left2 = wheat - meals_this_step
        # Estimate farm output from those still farming
        still_farming = [c for c in components if id(c) not in assigned and c.steps_since_meal < 3]
        farm_out = sum(5 if c.role == "Farmer" else 2 for c in still_farming)
        # Only eat at 3 if after eating + farming we'd have plenty for next step's mandatory meals
        next_step_mandatory = future_meal_demand - meals_this_step  # rough
        if wheat_left2 + farm_out - next_step_mandatory >= 6:
            for c in components:
                if id(c) in assigned:
                    continue
                if c.steps_since_meal == 3 and c.role != "Warrior":
                    # Only farmers, save warriors for farming/cave
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))
                    wheat_left2 -= 1  # track

        # PRIORITY 5: Everyone else farms
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        assigned = set()

        # Sort most hungry first
        sorted_comps = sorted(components, key=lambda c: -c.steps_since_meal)

        for c in sorted_comps:
            if id(c) in assigned:
                continue

            # MUST return at meal >= 4 (will be at 5 arriving village, eat at 6 = starving)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Attack! (meal 0,1,2,3 are all safe - attack until meal 3, then return)
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```