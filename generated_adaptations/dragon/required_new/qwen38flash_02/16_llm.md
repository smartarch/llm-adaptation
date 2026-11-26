

Looking at the consistent 0% win rate, the core issues are:

1. **Warriors sent at meal=2 or 3 arrive at cave at meal=3 or 4**, and immediately return without attacking (or with just 1 attack). This wastes trips.
2. **I need to send warriors at meal ≤ 1** so they get 2+ attacks per trip.
3. **Not spawning fast enough** — with only 2-3 initial warriors, 6-step cycles can't maintain 2 attackers.
4. **Eating threshold too late** — must eat at meal ≥ 4 (not 5) because travel takes 1 step.

**New approach — "guarantee 1 attacker every step":**
- Send warriors at meal ≤ 1 (arrive at meal ≤ 2, attack at 2→3→4, 2-3 attacks guaranteed)
- Always send if no one with meal ≤ 3 is currently attacking in cave
- Spawn warriors aggressively whenever wheat ≥ 12
- Eat at meal ≥ 4 (mandatory constraint), eat at meal = 3 only if wheat is abundant
- In cave: attack unless meal ≥ 4 or HP ≤ 1 (must leave at 4, arrive village at 5, eat at 5 = deadline)

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
        meals_spent = 0

        # Who is currently in cave AND still able to attack (meal <= 3)?
        cave_active = [v for v in list(environment.warriors) + list(environment.farmers)
                       if v.location == "Cave" and v.steps_since_meal <= 3]
        # Warriors in cave about to leave (meal >= 4) — they arrive village next step at meal 5
        cave_coming_home = sum(1 for v in list(environment.warriors) + list(environment.farmers)
                               if v.location == "Cave" and v.steps_since_meal >= 3)
        # Warriors we're sending this step arrive next step, count them as incoming
        sending_now = 0

        # ===== EAT (mandatory: meal >= 4 must eat now) =====
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if c.steps_since_meal >= 4 and meals_spent < wheat:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                meals_spent += 1

        # ===== SEND warriors to cave =====
        # Need at least 1-2 attackers every step. Check if cave is covered.
        # cave_active counts those who can still attack. If < 2, send replacements.
        # Also: cave_coming_home will be gone next step, so subtract them.
        effective_current = max(0, len(cave_active) - sum(1 for v in environment.warriors + environment.farmers
                                                          if v.location == "Cave" and v.steps_since_meal == 3))
        # effective_current ≈ those who will still attack next step

        target = 2 if dragon_hp > 30 else 4
        deficit = max(0, target - effective_current)

        # Send warriors at meal <= 1 (guarantees 2+ attacks per trip)
        sendable = sorted(
            [c for c in components
             if id(c) not in assigned and c.role == "Warrior"
             and c.steps_since_meal <= 1 and c.hp >= 2],
            key=lambda c: c.steps_since_meal
        )

        for w in sendable:
            if sending_now >= max(2, deficit):
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sending_now += 1

        # If desperate (cave empty, dragon not dead), send farmers too
        if effective_current == 0 and sending_now == 0:
            for c in sorted(
                [c for c in components if id(c) not in assigned and c.steps_since_meal <= 1 and c.hp >= 2],
                key=lambda c: (c.role == "Farmer", c.steps_since_meal)
            ):
                if sending_now >= 2:
                    break
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                sending_now += 1

        # ===== SPAWN warriors aggressively =====
        remaining = [c for c in components if id(c) not in assigned]
        total_warriors = len(environment.warriors)

        # Can we afford spawn? wheat - meals - reserve >= 12
        # Reserve: cave_coming_home will arrive and need food next step (1 each)
        reserve = cave_coming_home
        can_spawn = (wheat - meals_spent - reserve >= 12
                     and len(remaining) >= 4
                     and total_warriors < 10)

        if can_spawn:
            # Use 2 non-critical villagers (prefer farmers)
            pool = sorted(remaining, key=lambda c: (c.role == "Warrior", c.steps_since_meal))
            if len(pool) >= 2:
                environment.assign_group(pool[0], "spawn warrior")
                assigned.add(id(pool[0]))
                environment.assign_group(pool[1], "spawn warrior")
                assigned.add(id(pool[1]))

        # ===== Optional eat at meal 3 if abundant wheat =====
        if wheat > meals_spent + reserve + 10:
            for c in components:
                if id(c) in assigned:
                    continue
                if c.steps_since_meal == 3 and meals_spent < wheat:
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))
                    meals_spent += 1
                    break

        # ===== FARM all remaining =====
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        assigned = set()

        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue

            # MUST return at meal >= 4: arrive village next step at meal 5, eat then.
            # (Constraint: must not stay in cave at meal 4 — checker flags this.)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Return if critically low HP (avoid being eaten by dragon)
            if c.hp <= 1:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # ATTACK the dragon — never idle in cave, that wastes the trip
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```