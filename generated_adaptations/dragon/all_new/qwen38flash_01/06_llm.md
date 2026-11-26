

Looking at the failures, the key issues are:

1. **Starving in cave**: My "keep one attacking" edge case was forcing villagers with ssm >= 4 to stay in cave. Must ALWAYS send ssm >= 4 back to village.
2. **Dragon not killed**: Not enough warriors in cave, not spawning aggressively enough.
3. **Spawn logic**: Need to spawn when < 5 villagers, and spawn warriors when none exist.

The warrior cycle should be: Eat → Move to Cave → Attack × 3 → Move to Village → Eat (6 steps, 3 attacks). With 3+ warriors staggered, dragon is always attacked.

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
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)
        total_villagers = len(all_warriors) + len(all_farmers)
        num_warriors = len(all_warriors)

        # Priority 1: MUST eat (ssm >= 5, next step = 6 = starve)
        must_eat = [c for c in components if c.steps_since_meal >= 5]
        remaining = [c for c in components if c.steps_since_meal < 5]
        for c in must_eat:
            environment.assign_group(c, "eat")

        if not remaining:
            return

        # Split by role
        farmers_free = [c for c in remaining if c.role == "Farmer"]
        warriors_free = [c for c in remaining if c.role == "Warrior"]

        # Count how many warriors are in cave right now
        warriors_in_cave = sum(1 for v in all_warriors if v.location == "Cave")
        farmers_in_cave = sum(1 for v in all_farmers if v.location == "Cave")

        # Spawn decisions
        # Reserve wheat for meals: each villager eats roughly every 6 steps
        wheat_for_meals = total_villagers + 3
        wheat_available = max(0, wheat - wheat_for_meals)

        spawn_pool = list(farmers_free) + list(warriors_free)
        spawned_any = False

        # Rule: when < 5 villagers, spawn if we have 2+ free villagers and wheat
        if total_villagers < 5 and len(spawn_pool) >= 2:
            if wheat_available >= 10:
                c1 = spawn_pool.pop(0)
                c2 = spawn_pool.pop(0)
                environment.assign_group(c1, "spawn farmer")
                environment.assign_group(c2, "spawn farmer")
                spawned_any = True
            elif wheat_available >= 12:
                c1 = spawn_pool.pop(0)
                c2 = spawn_pool.pop(0)
                environment.assign_group(c1, "spawn warrior")
                environment.assign_group(c2, "spawn warrior")
                spawned_any = True

        # Rule: when no warriors exist (or very few in cave), spawn warriors
        if not spawned_any and num_warriors == 0 and len(spawn_pool) >= 2 and wheat_available >= 12:
            c1 = spawn_pool.pop(0)
            c2 = spawn_pool.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            spawned_any = True

        # Rule: if warriors_in_cave < 3 and we can afford it, spawn warriors
        if not spawned_any and warriors_in_cave < 3 and len(spawn_pool) >= 2 and wheat_available >= 12:
            c1 = spawn_pool.pop(0)
            c2 = spawn_pool.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            spawned_any = True

        # Now assign remaining components
        # Warriors with low ssm should go to cave immediately
        warriors_to_cave = []
        warriors_to_farm = []
        for c in warriors_free:
            if c.steps_since_meal <= 1:
                warriors_to_cave.append(c)
            elif c.steps_since_meal <= 2:
                # Can still make it: move(1) arrive ssm=3, attack ssm=4, must leave next
                # Actually ssm=2: move arrives ssm=3, attack ssm=4, then must go back
                # Only worth if dragon is nearly dead
                if dragon_hp <= 10:
                    warriors_to_cave.append(c)
                else:
                    warriors_to_farm.append(c)
            else:
                warriors_to_farm.append(c)

        for c in warriors_to_cave:
            environment.assign_group(c, "cave")

        # Farmers: minimum farming, rest either farm or go to cave in late game
        min_farmers = 1 if total_villagers <= 3 else 2
        farmers_for_farm = farmers_free[:min_farmers]
        farmers_surplus = farmers_free[min_farmers:]

        for c in farmers_for_farm:
            environment.assign_group(c, "farm")

        # Late game: send surplus farmers to cave
        if dragon_hp <= 15:
            for c in farmers_surplus:
                environment.assign_group(c, "cave")
        elif dragon_hp <= 30 and warriors_in_cave < 2:
            for c in farmers_surplus:
                environment.assign_group(c, "cave")
        else:
            # Keep farming for wheat production
            for c in farmers_surplus:
                environment.assign_group(c, "farm")

        # Remaining warriors in spawn pool that weren't spawned
        # They were already counted in farmers_free/warriors_free, so skip
        # Actually warriors_free was consumed by warriors_to_cave/farm above
        # The spawn_pool might have had some warriors from warriors_free
        # Need to handle those that were in spawn_pool but not spawned

        # Rebuild: components not yet assigned
        assigned_ids = set()
        for c in must_eat:
            assigned_ids.add(id(c))
        for c in warriors_to_cave:
            assigned_ids.add(id(c))
        for c in farmers_for_farm:
            assigned_ids.add(id(c))
        # Count spawned
        spawned_components = []
        for group in ["spawn farmer", "spawn warrior"]:
            pass  # Can't track easily, use a different approach

        # Simpler: just assign all remaining to farm
        for c in components:
            if id(c) not in assigned_ids:
                # Check if already assigned to spawn
                # We can't easily check, so just try to assign
                # Actually we assigned some from spawn_pool which overlaps with farmers_free/warriors_free
                # Let me redo this more carefully
                pass

        # Redo: track assignments explicitly
        # Clear and redo all assignments
        # ... Actually the environment just calls assign_group, last one wins?
        # No, we should only assign once. Let me restructure.

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        # CRITICAL: ssm >= 4 in cave → MUST go to village NOW
        # Travel takes 1 step, arrive with ssm=5, eat next step at ssm=5→0
        # If ssm=5 in cave, travel → arrive ssm=6 = STARVING!
        # If ssm=4 in cave, travel → arrive ssm=5, eat → ssm=0. OK.
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```

Wait, I have a bug in `assign_in_village` - the spawn pool overlaps with farmers_free/warriors_free, so some components get assigned twice. Let me rewrite cleanly:

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
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)
        total_villagers = len(all_warriors) + len(all_farmers)
        num_warriors = len(all_warriors)
        warriors_in_cave = sum(1 for v in all_warriors if v.location == "Cave")

        # Track which components are already assigned
        assigned = set()

        # Step 1: Must eat (ssm >= 5)
        for c in components:
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                assigned.add(id(c))

        if len(assigned) == len(components):
            return

        # Remaining unassigned components, split by role
        remaining_farmers = [c for c in components if id(c) not in assigned and c.role == "Farmer"]
        remaining_warriors = [c for c in components if id(c) not in assigned and c.role == "Warrior"]

        # Wheat budget: reserve meals, use rest for spawning
        wheat_for_meals = total_villagers + 3
        wheat_available = max(0, wheat - wheat_for_meals)

        # Build spawn pool from surplus (exclude minimum farmers needed)
        min_farmers = 1 if total_villagers <= 3 else 2
        # Reserve min_farmers farmers for farming
        farmers_pool = list(remaining_farmers)
        warriors_pool = list(remaining_warriors)

        # Separate farmers needed for farming from those available for spawn/cave
        farmers_for_farming = farmers_pool[:min_farmers]
        farmers_excess = farmers_pool[min_farmers:]

        # Spawn pool = excess farmers + warriors with high ssm (can't go to cave)
        spawn_pool_farmers = list(farmers_excess)
        spawn_pool_warriors = [c for c in warriors_pool if c.steps_since_meal >= 3]
        # Warriors with low ssm should go to cave, not spawn
        warriors_low_ssm = [c for c in warriors_pool if c.steps_since_meal < 3]

        # Attempt spawns
        spawn_attempts = []
        if total_villagers < 5 and wheat_available >= 10:
            spawn_attempts.append(("spawn farmer", 10))
        if num_warriors == 0 or warriors_in_cave < 3:
            if wheat_available >= 12:
                spawn_attempts.append(("spawn warrior", 12))
        elif wheat_available >= 22:
            spawn_attempts.append(("spawn farmer", 10))

        for group_name, cost in spawn_attempts:
            pool = spawn_pool_farmers + spawn_pool_warriors
            while len(pool) >= 2 and wheat_available >= cost:
                # Prefer using farmers from pool
                if spawn_pool_farmers and len(spawn_pool_farmers) >= 2:
                    c1 = spawn_pool_farmers.pop(0)
                    c2 = spawn_pool_farmers.pop(0)
                elif spawn_pool_farmers and spawn_pool_warriors:
                    c1 = spawn_pool_farmers.pop(0)
                    c2 = spawn_pool_warriors.pop(0)
                elif len(spawn_pool_warriors) >= 2:
                    c1 = spawn_pool_warriors.pop(0)
                    c2 = spawn_pool_warriors.pop(0)
                else:
                    break
                environment.assign_group(c1, group_name)
                environment.assign_group(c2, group_name)
                assigned.add(id(c1))
                assigned.add(id(c2))
                wheat_available -= cost

        # Assign warriors with low ssm to cave
        for c in warriors_low_ssm:
            if id(c) not in assigned:
                environment.assign_group(c, "cave")
                assigned.add(id(c))

        # Assign remaining warriors to farm (they'll eat/farm then go later)
        for c in spawn_pool_warriors:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

        # Assign farmers for farming
        for c in farmers_for_farming:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

        # Assign remaining excess farmers
        for c in spawn_pool_farmers:
            if id(c) not in assigned:
                # Late game: send to cave to help
                if dragon_hp <= 20:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
                assigned.add(id(c))

        # Any remaining unassigned
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        # CRITICAL: ssm >= 4 in cave → MUST go to village
        # Move takes 1 step: ssm=4 → arrive ssm=5 → eat (safe)
        # ssm=5 → arrive ssm=6 → STARVE. Must have left at ssm=4.
        for c in components:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```