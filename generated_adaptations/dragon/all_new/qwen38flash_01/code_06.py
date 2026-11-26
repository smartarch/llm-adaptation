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