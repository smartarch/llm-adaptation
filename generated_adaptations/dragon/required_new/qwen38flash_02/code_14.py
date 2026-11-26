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

        # Current attackers in cave
        num_cave = sum(1 for v in list(environment.warriors) + list(environment.farmers)
                       if v.location == "Cave")

        # ===== STEP 1: EAT those who must eat (meal >= 4) =====
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if c.steps_since_meal >= 4 and meals_used < wheat:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                meals_used += 1

        # ===== STEP 2: SEND warriors to cave =====
        # Target: 3+ attackers in cave; send aggressively when undermanned
        target = 3
        if dragon_hp <= 25:
            target = 5
        if num_cave == 0:
            target = 6  # emergency: send everyone possible

        need = max(0, target - num_cave)
        sent = 0

        # Prefer warriors with lowest meal (most room before must-return)
        send_candidates = sorted(
            [c for c in components
             if id(c) not in assigned and c.role == "Warrior"
             and c.steps_since_meal <= 3 and c.hp >= 1],
            key=lambda c: c.steps_since_meal
        )

        for w in send_candidates:
            if sent >= need:
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sent += 1

        # If still no attackers in cave, throw farmers in too
        if num_cave == 0 and sent < need:
            for c in sorted(
                [c for c in components
                 if id(c) not in assigned and c.steps_since_meal <= 2 and c.hp >= 2],
                key=lambda c: c.steps_since_meal
            ):
                if sent >= need:
                    break
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                sent += 1

        # ===== STEP 3: SPAWN warriors when we have wheat surplus =====
        # Simple rule: spawn if wheat covers meals already used + 12 for spawn + 8 buffer
        remaining_count = sum(1 for c in components if id(c) not in assigned)
        total_warriors = len(environment.warriors)

        if (wheat - meals_used >= 14 and
            remaining_count >= 4 and
            total_warriors < 8):
            # Pick 2 villagers to spawn (prefer non-warriors so warriors keep farming/attacking)
            spawn_candidates = sorted(
                [c for c in components if id(c) not in assigned],
                key=lambda c: (c.role == "Warrior", c.steps_since_meal)
            )
            if len(spawn_candidates) >= 2:
                environment.assign_group(spawn_candidates[0], "spawn warrior")
                assigned.add(id(spawn_candidates[0]))
                environment.assign_group(spawn_candidates[1], "spawn warrior")
                assigned.add(id(spawn_candidates[1]))

        # ===== STEP 4: Optional eat at meal==3 to smooth future =====
        # Only if lots of wheat
        if wheat > meals_used + 10:
            for c in components:
                if id(c) in assigned:
                    continue
                if c.steps_since_meal == 3 and meals_used < wheat:
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))
                    meals_used += 1
                    break  # limit optional eats per step

        # ===== STEP 5: Everyone remaining farms =====
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        assigned = set()

        # Sort most hungry first
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue

            # MUST return: at meal >= 4, arriving in village at meal 5, eat at 5 → safe
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Return if nearly dead (avoid being eaten by dragon)
            if c.hp <= 1:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Attack the dragon!
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        # Safety: ensure all assigned
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")