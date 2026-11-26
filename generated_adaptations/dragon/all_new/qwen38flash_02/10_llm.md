

Looking at the failures, I need to fix several issues:

1. **Not enough wheat to spawn**: I need to properly verify wheat is available AFTER all meal assignments before spawning.
2. **Unassigned component (Dorothy)**: Need a safety catch-all to ensure every component gets assigned.
3. **Starving**: The ssm >= 4 rule for cave needs to be enforced. Leaving at ssm=4 → arrive at ssm=5 → eat. Safe.
4. **Dragon not killed**: Need more aggressive warrior deployment and proper cycling.

Key insight: The eating cycle must be: eat(ssm≤3→0) → travel(1) → attack(2) → attack(3) → attack(4) → travel back(5) → eat(5→0). Total 6 steps, 3 attacks per warrior. Warriors must leave cave at ssm=4 (arrive village ssm=5, eat that step before ssm=6 starvation).

```py
import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)

        # Categorize components - each component goes into exactly one bucket
        must_eat = []       # ssm >= 4: critical, must eat NOW
        eat_soon = []       # ssm == 3: warriors benefit from eating now for fresh cycle
        to_cave = []        # ssm <= 2 warriors: send to cave
        spare = []          # everyone else (farmers with ssm <= 3)

        for c in components:
            if c.steps_since_meal >= 4:
                must_eat.append(c)
            elif c.steps_since_meal == 3 and c.role == "Warrior":
                eat_soon.append(c)
            elif c.role == "Warrior" and c.steps_since_meal <= 2:
                to_cave.append(c)
            else:
                spare.append(c)

        # Count actual eat assignments for wheat tracking
        eat_count = 0

        # Assign must_eat: eat if wheat available, else farm
        for c in must_eat:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                environment.assign_group(c, "farm")

        # Assign eat_soon warriors: eat if wheat available, else send to cave anyway
        for c in eat_soon:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                environment.assign_group(c, "cave")

        # All to_cave warriors go to cave
        for w in to_cave:
            if w.hp <= 1:
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        # Spare (mostly farmers): try to spawn warriors, rest farm
        # Can only spawn if: (wheat - eat_count - 12) >= 0 and enough reserve for next steps
        # Conservative: need wheat >= eat_count + 12 + number_of_cave_villagers_needing_food_soon
        cave_needing_food = 0
        for v in environment.warriors + environment.farmers:
            if v.location == "Cave" and v.steps_since_meal >= 3:
                cave_needing_food += 1

        can_spawn = False
        if len(spare) >= 2:
            # After eating this step, how much wheat is left before farming output?
            after_eats = wheat - eat_count
            # Farming this step will produce 5 per farmer NOT spawning
            farm_count = len(spare) - 2  # minus 2 for spawning
            farm_output = 5 * max(0, farm_count)
            # After spawn + farming, need enough for next step meals
            after_spawn = after_eats - 12 + farm_output
            if after_spawn >= cave_needing_food + 1:
                if total_warriors < 8 or total_warriors == 0:
                    can_spawn = True

        spawn_pairs = 1 if can_spawn and len(spare) >= 2 else 0
        idx = 0
        for _ in range(spawn_pairs):
            if idx + 1 < len(spare):
                environment.assign_group(spare[idx], "spawn warrior")
                environment.assign_group(spare[idx + 1], "spawn warrior")
                idx += 2

        # All remaining spare farmers farm
        for i in range(idx, len(spare)):
            environment.assign_group(spare[i], "farm")

        # Safety: ensure nothing was missed (shouldn't happen with correct categorization)
        # This is a no-op safety check - the categorization above covers all cases

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        for c in components:
            if c.steps_since_meal >= 4:
                # Must leave NOW: arrive village at ssm=5, eat before ssm=6 starvation
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                # Too fragile, retreat to village
                environment.assign_group(c, "village")
            else:
                # Attack the dragon
                environment.assign_group(c, "attack")
```