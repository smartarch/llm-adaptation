

Looking at the 0% win rate, I've identified the fundamental problems:

1. **Attack coverage gaps**: When all warriors go in a group, they all attack together, then ALL travel back simultaneously, creating 2-3 step gaps where dragon regenerates +5 HP/step. This makes the dragon unkillable.

2. **Sending at wrong meal values**: Sending at meal=2 means arriving at meal=3 (1 attack), and meal=3 means arriving at meal=4 (0 attacks!). Need to send at meal=0 or 1.

3. **The golden window**: After eating (meal becomes 1 next step), warriors must be sent IMMEDIATELY. If they farm instead, they'll never get sent before being forced to eat again.

**Corrected strategy:**
- **Send warriors at meal ≤ 2** (arrive at meal 1-3, get 1-3 attacks). Prefer meal ≤ 1.
- **Send max 1 warrior per step** (natural staggering avoids synchronized gaps). Send 2 only if cave is empty.
- **Eat at meal ≥ 4 only if wheat is actually available** (no more constraint violations).
- **Reserve wheat for upcoming mandatory meals before spawning.**
- **In cave: attack at meal ≤ 3, return at meal ≥ 4.**

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
        wheat_spent = 0

        all_obs = list(environment.warriors) + list(environment.farmers)

        # How many will be attacking in cave NEXT step?
        # (cave dwellers with meal <= 2 who will still be in cave next step and not returning)
        will_be_attacking_next = sum(
            1 for v in all_obs
            if v.location == "Cave" and v.steps_since_meal <= 2
        )

        # ===== PRIORITY 1: EAT (meal >= 4 is mandatory) =====
        urgent = sorted(
            [c for c in components if c.steps_since_meal >= 4],
            key=lambda x: -x.steps_since_meal
        )
        for c in urgent:
            if wheat_spent < wheat:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                wheat_spent += 1
            else:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

        # ===== PRIORITY 2: SEND warriors to cave (staggered!) =====
        # Send 1 per step normally. 2 if cave will be empty.
        # Warriors at meal 0 or 1 are ideal (get 2-3 attacks after arrival).
        # Warriors at meal 2 still get 1 attack (arrive at 3, attack, return at 4).

        target = 2 if dragon_hp > 30 else 4
        deficit = max(0, target - will_be_attacking_next)

        # Sort by meal (lowest first = best candidates)
        sendable = sorted(
            [c for c in components
             if id(c) not in assigned and c.role == "Warrior"
             and c.steps_since_meal <= 2 and c.hp >= 1],
            key=lambda c: c.steps_since_meal
        )

        # Normal: send 1. Empty cave: send up to 2.
        max_this_step = 2 if will_be_attacking_next == 0 else 1

        sent = 0
        for w in sendable:
            if sent >= deficit or sent >= max_this_step:
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sent += 1

        # Emergency: cave will be empty, send farmers too (1 dmg prevents 5 regen)
        if will_be_attacking_next == 0 and sent == 0:
            emg = sorted(
                [c for c in components
                 if id(c) not in assigned and c.steps_since_meal <= 2 and c.hp >= 2],
                key=lambda c: (c.role != "Warrior", c.steps_since_meal)
            )
            for c in emg[:2]:
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                sent += 1

        # ===== PRIORITY 3: SPAWN warriors when affordable =====
        remaining = [c for c in components if id(c) not in assigned]
        total_warriors = len(environment.warriors)

        # Count upcoming mandatory meals: anyone at meal 3 will be at meal 4 next step
        # and might not have time to travel+eat (cave villagers especially).
        upcoming_meals = sum(
            1 for c in components if id(c) not in assigned and c.steps_since_meal == 3
        ) + sum(1 for v in all_obs if v.location == "Cave" and v.steps_since_meal == 3)

        # Only spawn if wheat covers: current meals + upcoming + spawn(12) + buffer
        if (wheat - wheat_spent >= 12 + upcoming_meals + 3
                and len(remaining) >= 4
                and total_warriors < 8):
            pool = sorted(remaining, key=lambda c: (c.role == "Warrior", c.steps_since_meal))
            if len(pool) >= 2:
                environment.assign_group(pool[0], "spawn warrior")
                assigned.add(id(pool[0]))
                environment.assign_group(pool[1], "spawn warrior")
                assigned.add(id(pool[1]))

        # ===== PRIORITY 4: Optional eat at meal 3 if wheat abundant =====
        if wheat - wheat_spent >= 8:
            for c in components:
                if id(c) in assigned:
                    continue
                if c.steps_since_meal == 3 and wheat_spent < wheat:
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))
                    wheat_spent += 1

        # ===== PRIORITY 5: Farm all remaining =====
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        assigned = set()

        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue

            # Must leave at meal >= 4 (arrive village at 5, eat at 5 = last safe step)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Return if nearly dead
            if c.hp <= 1:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Attack! (meal 0-3 all allow attacking)
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```