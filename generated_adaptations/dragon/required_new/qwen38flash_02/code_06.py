import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Count villagers in cave with meal >= 4: they MUST return to village,
        # arriving next step at meal=5, so they MUST eat next step.
        # Also count village villagers with meal >= 5 who couldn't eat (will need to eat next step too).
        cave_will_need_eat = sum(
            1 for v in (environment.warriors + environment.farmers)
            if v.location == "Cave" and v.steps_since_meal >= 4
        )

        # Village villagers who will need to eat next step:
        # those with meal >= 4 who don't eat this step will be at meal=5 next step.
        # We handle this by assigning them to eat THIS step if wheat allows.

        assigned = set()
        wheat_spent_on_meals = 0

        # PRIORITY 1: Assign to eat - villagers with meal >= 4 (must eat NOW)
        # Sort by most urgent first
        urgent_eat = sorted(
            [c for c in components if c.steps_since_meal >= 4],
            key=lambda c: -c.steps_since_meal
        )
        for c in urgent_eat:
            if wheat_spent_on_meals < wheat:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                wheat_spent_on_meals += 1
            # else: can't eat this step, will need to eat next step (at meal 5)
            # This is fine as long as we reserve wheat for next step

        # PRIORITY 2: Assign to eat - villagers with meal == 3 (should eat soon)
        # Only if we have surplus wheat after reserving for mandatory future meals
        # Future mandatory meals: cave_will_need_eat + village villagers at meal 4 who didn't eat
        village_meal4_not_eaten = sum(
            1 for c in urgent_eat if id(c) not in assigned
        )
        future_mandatory_meals = cave_will_need_eat + village_meal4_not_eaten

        # Estimate farming output this step (will add to wheat)
        remaining_for_farming = [c for c in components if id(c) not in assigned and c.steps_since_meal < 3]
        farm_output_estimate = sum(5 if c.role == "Farmer" else 2 for c in remaining_for_farming)

        # Wheat after this step (conservative): wheat - meals - spawn_costs + farm_output
        # We want: wheat_after >= future_mandatory_meals
        # So available for extra meals/spawning: wheat - future_mandatory_meals (conservative, ignore farm output for safety)

        surplus_after_mandatory = wheat - wheat_spent_on_meals - future_mandatory_meals
        surplus_after_mandatory = max(0, surplus_after_mandatory)

        moderate_eat = [c for c in components if c.steps_since_meal == 3 and id(c) not in assigned]
        for c in moderate_eat:
            if surplus_after_mandatory > 0:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                surplus_after_mandatory -= 1
                wheat_spent_on_meals += 1

        # PRIORITY 3: Send warriors to cave for attack rotation
        cave_warriors = [w for w in environment.warriors if w.location == "Cave"]
        cave_farmers = [f for f in environment.farmers if f.location == "Cave"]
        num_in_cave = len(cave_warriors) + len(cave_farmers)

        # Target attackers in cave: need continuous coverage
        # Warriors can last 3 steps in cave (meal 0,1,2 → attack, attack, travel back)
        # Actually: meal 0→1, 1→2, 2→3, at 3 still safe (attack step where meal=3, then at 4 travel)
        # So warriors can attack for steps where meal is 0,1,2,3 (4 attack steps) then travel at meal=4
        # Wait: if they arrive with meal=0, attack meal 0→1, attack 1→2, attack 2→3, at 3 attack→4, at 4 travel back
        # That's 4 attacks then travel. But we don't want to push too hard due to dragon counterattack.
        # Safe: attack at meal 0,1,2 (3 attacks), travel at meal 3. Arrive at meal 4, eat.

        # Target: keep ~4 warriors attacking at a time for good DPS
        # Each warrior does 3 damage × 3 attacks = 9 damage per cycle (~5 steps: 1 travel + 3 attack + 1 travel)
        # Need: 100 HP / 12 damage per step (4 warriors) ≈ 9 steps minimum

        target_cave = 4 if dragon_hp > 20 else 6
        target_cave = min(target_cave, num_in_cave + len([c for c in components if id(c) not in assigned and c.role == "Warrior" and c.steps_since_meal <= 1]))

        need_to_send = max(0, target_cave - num_in_cave)

        remaining = [c for c in components if id(c) not in assigned]
        village_warriors = sorted(
            [c for c in remaining if c.role == "Warrior" and c.steps_since_meal <= 1],
            key=lambda c: c.steps_since_meal
        )

        sent = 0
        for w in village_warriors:
            if sent >= need_to_send:
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sent += 1

        # If desperate (no attackers in cave), send more aggressively
        if num_in_cave == 0 and sent < need_to_send:
            desperate = sorted(
                [c for c in components if id(c) not in assigned and c.role == "Warrior" and c.steps_since_meal <= 2 and c.hp >= 2],
                key=lambda c: c.steps_since_meal
            )
            for w in desperate:
                if sent >= need_to_send:
                    break
                environment.assign_group(w, "cave")
                assigned.add(id(w))
                sent += 1

        # If still no attackers and dragon is low, throw farmers in too
        if num_in_cave == 0 and sent == 0 and dragon_hp <= 20:
            desperate_f = sorted(
                [c for c in components if id(c) not in assigned and c.steps_since_meal <= 2 and c.hp >= 2],
                key=lambda c: c.steps_since_meal
            )
            for c in desperate_f[:2]:
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                sent += 1

        # PRIORITY 4: Spawn warriors if wheat allows and we have enough spare villagers
        remaining = [c for c in components if id(c) not in assigned]
        # Check if we can afford spawning: need 12 wheat AND must not create future food shortage
        # Future meals after spawning: new warriors will need food
        total_villagers_after_spawn = len(environment.warriors) + len(environment.farmers) + 1
        estimated_daily_food = total_villagers_after_spawn  # roughly 1 wheat per villager per 6 steps
        # Conservative: only spawn if wheat after meals is significantly surplus
        wheat_after_current_meals = wheat - wheat_spent_on_meals
        # Farming this step will produce some wheat; estimate from remaining farmers/warriors still farming
        still_remaining = [c for c in remaining if id(c) not in assigned]
        farm_output = sum(5 if c.role == "Farmer" else 2 for c in still_remaining if c.steps_since_meal < 3)
        # Also add farming from those not eating (meal 0-2)
        farm_from_others = sum(
            5 if c.role == "Farmer" else 2
            for c in components
            if id(c) not in assigned and c.steps_since_meal < 3
        )
        estimated_wheat_after = wheat_after_current_meals + farm_output

        # Can we afford spawn (12) AND still have enough for future meals?
        can_spawn = (estimated_wheat_after >= 12 + future_mandatory_meals + 6) and len(remaining) >= 4
        # Don't spawn too many warriors (food cost grows); cap at reasonable number
        total_warriors = len(environment.warriors)
        can_spawn = can_spawn and total_warriors < 8

        if can_spawn:
            # Use 2 farmers to spawn (farmers are less valuable in cave)
            farmer_candidates = [c for c in remaining if id(c) not in assigned and c.role == "Farmer"]
            other_candidates = [c for c in remaining if id(c) not in assigned and c.role != "Farmer"]
            spawn_pool = farmer_candidates[:2] + other_candidates[:2]
            spawn_pool = spawn_pool[:2]  # exactly 2

            if len(spawn_pool) == 2:
                environment.assign_group(spawn_pool[0], "spawn warrior")
                environment.assign_group(spawn_pool[1], "spawn warrior")
                assigned.add(id(spawn_pool[0]))
                assigned.add(id(spawn_pool[1]))
                remaining = [c for c in components if id(c) not in assigned]

        # PRIORITY 5: Everyone remaining farms
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        assigned = set()

        # Sort by meal urgency (most urgent first)
        sorted_comps = sorted(components, key=lambda c: -c.steps_since_meal)

        for c in sorted_comps:
            if id(c) in assigned:
                continue

            # At meal >= 4, MUST return to village (unconditionally - constraint requirement)
            # They'll arrive next step at meal=5 and must eat then
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # At meal == 3, one more attack then travel next step
            # Safe to attack (will be meal=4 next step, then travel)
            # Attack!
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        # Safety: ensure all assigned
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")