import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        assigned = set()
        meals_used = 0

        all_observed = list(environment.warriors) + list(environment.farmers)

        # Count attackers currently in cave
        num_in_cave = sum(1 for v in all_observed if v.location == "Cave")

        # Count villagers in cave with meal >= 4: they will return and must eat next step
        cave_returners_eating_next = sum(
            1 for v in all_observed if v.location == "Cave" and v.steps_since_meal >= 3
        )

        # PRIORITY 1: Mandatory eat (meal >= 4 in village = must eat now)
        urgent_eaters = sorted(
            [c for c in components if c.steps_since_meal >= 4],
            key=lambda c: -c.steps_since_meal
        )
        for c in urgent_eaters:
            if meals_used < wheat:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                meals_used += 1
            else:
                # No wheat available; assign to farm (will starve but nothing better)
                environment.assign_group(c, "farm")
                assigned.add(id(c))

        # PRIORITY 2: Send warriors to cave aggressively
        # Target: at least 3 attackers in cave at all times for 9 dmg/step
        target_attackers = 3
        if dragon_hp <= 30:
            target_attackers = 5

        need = max(0, target_attackers - num_in_cave)

        # Candidates: warriors in village with meal <= 3 (safe cycle)
        warriors_avail = sorted(
            [c for c in components
             if id(c) not in assigned and c.role == "Warrior"
             and c.steps_since_meal <= 3 and c.hp >= 2],
            key=lambda c: c.steps_since_meal
        )

        sent = 0
        for w in warriors_avail:
            if sent >= need:
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sent += 1

        # Still need attackers? Send farmers too (1 dmg but prevents regen)
        if sent < need and num_in_cave == 0:
            farmers_avail = sorted(
                [c for c in components
                 if id(c) not in assigned and c.steps_since_meal <= 2 and c.hp >= 2],
                key=lambda c: c.steps_since_meal
            )
            for f in farmers_avail:
                if sent >= need:
                    break
                environment.assign_group(f, "cave")
                assigned.add(id(f))
                sent += 1

        # PRIORITY 3: Spawn warriors aggressively
        # Wheat after mandatory meals, minus reserve for upcoming meals
        wheat_after_meals = wheat - meals_used
        # Upcoming mandatory meals: cave_returners + village villagers at meal 3 who will be at 4 next step
        village_meal3 = sum(1 for c in components if c.steps_since_meal == 3 and id(c) not in assigned)
        future_mandatory = cave_returners_eating_next + village_meal3
        # Farming output this step
        remaining_now = [c for c in components if id(c) not in assigned]
        farm_output = sum(5 if c.role == "Farmer" else 2 for c in remaining_now)
        projected = wheat_after_meals + farm_output

        total_pop = len(environment.warriors) + len(environment.farmers)
        total_warriors = len(environment.warriors)

        # Spawn if we can afford it and won't create food crisis
        if projected >= 12 + future_mandatory + 3 and total_warriors < 10 and total_pop < 14:
            # Use 2 villagers (prefer farmers) for spawn
            spawn_pool = [c for c in remaining_now if id(c) not in assigned]
            spawn_pool.sort(key=lambda c: (c.role == "Warrior", c.steps_since_meal))
            if len(spawn_pool) >= 4:  # Keep enough for farming
                for s in spawn_pool[:2]:
                    environment.assign_group(s, "spawn warrior")
                    assigned.add(id(s))
                    remaining_now = [c for c in components if id(c) not in assigned]

        # PRIORITY 4: Optional eat at meal 3 to prevent future pressure
        # Only if we have wheat surplus
        remaining_now = [c for c in components if id(c) not in assigned]
        if wheat_after_meals > future_mandatory + 4:
            for c in remaining_now:
                if c.steps_since_meal == 3 and c.role == "Farmer":
                    if meals_used < wheat:
                        environment.assign_group(c, "eat")
                        assigned.add(id(c))
                        meals_used += 1

        # PRIORITY 5: Everyone remaining farms
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        assigned = set()

        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue

            # MUST return at meal >= 4: arrive village at 5, eat at 5. Safe.
            # If meal >= 5 in cave, they're about to starve, return NOW.
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Attack the dragon! This prevents 5 HP regen.
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")