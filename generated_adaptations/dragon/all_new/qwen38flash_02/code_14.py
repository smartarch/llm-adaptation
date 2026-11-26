import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)
        dragon_hp = environment.dragon.hp

        # Endgame: dragon is nearly dead, send everyone to attack
        if dragon_hp <= 30:
            for c in components:
                if c.steps_since_meal >= 4:
                    if wheat >= 1:
                        environment.assign_group(c, "eat")
                        wheat -= 1
                    else:
                        environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, "cave")
            return

        # Categorize components - each goes into exactly one bucket
        must_eat = []       # ssm >= 4: critical
        eat_reset = []      # warriors ssm 2-3: eat to reset for fresh cycle
        to_cave = []        # warriors ssm <= 1: send to cave
        farmers_avail = []  # farmers with ssm <= 3: farm or spawn

        for c in components:
            if c.steps_since_meal >= 4:
                must_eat.append(c)
            elif c.role == "Warrior" and c.steps_since_meal >= 2:
                eat_reset.append(c)
            elif c.role == "Warrior":
                to_cave.append(c)
            else:
                farmers_avail.append(c)

        eat_count = 0

        # Critical eaters: eat if wheat available, else farm
        for c in must_eat:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                environment.assign_group(c, "farm")

        # Warriors with ssm 2-3: eat to reset (avoids only getting 1 attack in cave)
        for c in eat_reset:
            if (wheat - eat_count) >= 1:
                environment.assign_group(c, "eat")
                eat_count += 1
            else:
                # No wheat to eat - farm instead, don't waste cave trip
                environment.assign_group(c, "farm")

        # Fresh warriors (ssm <= 1) go to cave
        for w in to_cave:
            if w.hp <= 1:
                environment.assign_group(w, "farm")
            else:
                environment.assign_group(w, "cave")

        # Farmers: try to spawn warriors aggressively
        # Count upcoming meal needs over next ~4 steps
        upcoming_meals = 0
        for v in environment.warriors + environment.farmers:
            if v.steps_since_meal >= 2:
                upcoming_meals += 1

        after_eats = wheat - eat_count

        # Decide how many farmer pairs to spawn warriors
        # Always keep at least 2 farmers farming (10 wheat/step minimum)
        min_farm = 2
        max_spawn_pairs = max(0, (len(farmers_avail) - min_farm) // 2)

        # Limit spawns by wheat: each warrior costs 12
        # After spawning, need enough for upcoming meals
        max_by_wheat = 0
        for pairs in range(1, max_spawn_pairs + 1):
            cost = 12 * pairs
            farm_count = len(farmers_avail) - 2 * pairs
            farm_output = 5 * max(0, farm_count)
            remaining = after_eats - cost + farm_output
            if remaining >= upcoming_meals:
                max_by_wheat = pairs
            else:
                break

        # Be aggressive: spawn if wheat allows, especially when warrior count is low
        spawn_pairs = 0
        if total_warriors == 0:
            spawn_pairs = max_by_wheat  # critical
        elif total_warriors < 6:
            spawn_pairs = max_by_wheat
        elif total_warriors < 10 and after_eats >= 12 + upcoming_meals:
            spawn_pairs = min(max_by_wheat, 1)

        spawn_pairs = min(spawn_pairs, max_by_wheat)

        idx = 0
        for _ in range(spawn_pairs):
            if idx + 1 < len(farmers_avail):
                environment.assign_group(farmers_avail[idx], "spawn warrior")
                environment.assign_group(farmers_avail[idx + 1], "spawn warrior")
                idx += 2

        # All remaining farmers farm
        for i in range(idx, len(farmers_avail)):
            environment.assign_group(farmers_avail[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            if c.steps_since_meal >= 4:
                # Must leave: arrive village at ssm=5, eat before ssm=6
                environment.assign_group(c, "village")
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                # Attack the dragon every step
                environment.assign_group(c, "attack")