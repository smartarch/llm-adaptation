

Looking at the failures:

1. **Required test failures**: Assigning to "eat" when wheat < 1 causes an error. Also need to reserve wheat for upcoming meals.
2. **Optional test hints**: Warriors should eat when ssm >= 3 so they arrive fresh at cave and attack at least 2-3 times before leaving.

The key fixes:
- Check wheat > 0 before assigning to "eat"; if no wheat, assign to "farm" instead
- Reserve wheat for upcoming meals before spawning
- Warriors eat at ssm >= 3 (so they arrive at cave with ssm=1, can attack 3+ times)
- Warriors leave cave at ssm >= 5 (arrive village at ssm=6, eat immediately)
- Ensure all components get assigned even in edge cases

```py
import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        all_villagers = environment.warriors + environment.farmers
        total_warriors = len(environment.warriors)
        total_villagers = len(all_villagers)

        # Count how many villagers (including in cave) will need to eat within 2 steps
        # We need to reserve this wheat
        upcoming_meals = 0
        for v in all_villagers:
            if v.steps_since_meal >= 3:
                upcoming_meals += 1

        # Categorize village components
        urgent_eaters = [c for c in components if c.steps_since_meal >= 4]
        warriors_needing_food = [c for c in components if c.steps_since_meal == 3 and c.role == "Warrior"]
        rest = [c for c in components if c.steps_since_meal < 3 or (c.steps_since_meal == 3 and c.role == "Farmer")]

        # Assign urgent eaters (ssm >= 4) - eat if wheat available, else farm
        wheat_spent = 0
        for c in urgent_eaters:
            if wheat - wheat_spent >= 1:
                environment.assign_group(c, "eat")
                wheat_spent += 1
            else:
                # No wheat available, must farm to produce
                environment.assign_group(c, "farm")

        # Warriors with ssm == 3 should eat to arrive fresh at cave
        for c in warriors_needing_food:
            if wheat - wheat_spent >= 1:
                environment.assign_group(c, "eat")
                wheat_spent += 1
            else:
                # No wheat, send to cave anyway (will leave soon)
                environment.assign_group(c, "cave")

        # Remaining: warriors go to cave, farmers farm or spawn
        warriors = [c for c in rest if c.role == "Warrior"]
        farmers = [c for c in rest if c.role == "Farmer"]

        # All remaining warriors go to cave
        for w in warriors:
            if w.hp <= 1:
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        # Decide spawning for farmers
        # Available wheat after meals and this step's spawning
        # Farming will produce 5*wheat but that's end-of-step, so use current wheat minus meals
        available_wheat = wheat - wheat_spent
        # Reserve for upcoming meals (next 2 steps)
        reserve = upcoming_meals

        # Try to spawn warriors aggressively
        if len(farmers) >= 2:
            # Check if we can afford spawning + still have reserve
            # Spawning consumes wheat NOW, farming adds wheat at end of step
            # So we need: available_wheat - spawn_cost >= 0 (can't go negative)
            # And ideally reserve is maintained

            if total_warriors == 0 and available_wheat >= 12:
                # Critical: no warriors, spawn one ASAP
                environment.assign_group(farmers[0], "spawn warrior")
                environment.assign_group(farmers[1], "spawn warrior")
                farmers = farmers[2:]
            elif total_warriors < 6 and available_wheat >= 12 + reserve:
                # Keep growing warriors
                environment.assign_group(farmers[0], "spawn warrior")
                environment.assign_group(farmers[1], "spawn warrior")
                farmers = farmers[2:]
            elif total_villagers < 5 and available_wheat >= 10 + reserve:
                # Need more villagers overall
                if total_warriors >= 3 and available_wheat >= 12 + reserve:
                    environment.assign_group(farmers[0], "spawn warrior")
                    environment.assign_group(farmers[1], "spawn warrior")
                    farmers = farmers[2:]
                else:
                    environment.assign_group(farmers[0], "spawn farmer")
                    environment.assign_group(farmers[1], "spawn farmer")
                    farmers = farmers[2:]

        # Remaining farmers farm
        for f in farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 5:
                # Must return to village immediately to eat
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                # Too fragile, retreat
                environment.assign_group(c, "village")
            elif dragon_base and environment.dragon.hp <= 0:
                # Dragon dead, nothing to do
                environment.assign_group(c, "village")
            else:
                # Attack the dragon
                environment.assign_group(c, "attack")
```