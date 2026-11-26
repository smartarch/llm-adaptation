

Looking at the failures, my conservative fixes broke the attack rotation. The win rate dropped from 100% to 0% because:

1. **Tight rotation wasn't maintained**: I was sending warriors only at meal≤1, and many had meal=2-3, leaving the cave empty for stretches.
2. **Dragon regen (5 HP/step)** punishes any gap in attacks severely.
3. **Wheat reservation was too conservative**, blocking necessary spawns and attacks.

**New strategy:**
- Send warriors to cave as soon as meal ≤ 1 (so they get 3-4 attacks before returning at meal=4).
- Stagger: send max 1 warrior per step to maintain continuous coverage.
- Always ensure wheat for current mandatory eaters (meal≥4) before doing anything else.
- Reserve wheat for next-step mandatory eaters when deciding on spawns.
- Spawn warriors aggressively — more warriors = more DPS to beat 30-step limit.
- In cave: attack at meal ≤ 3, return unconditionally at meal ≥ 4.
- Late game desperation: if dragon HP low and cave empty, send anyone.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        all_villagers = list(environment.warriors) + list(environment.farmers)

        # Villagers in cave with meal>=3 will return and need to eat soon.
        # Those at meal 3 return at meal 4 (arrive next step at 4, eat next-next)
        # Those at meal 4 return at meal 5 (arrive next step at 5, MUST eat next step)
        cave_must_eat_next = sum(1 for v in all_villagers if v.location == "Cave" and v.steps_since_meal >= 4)
        cave_will_need_soon = sum(1 for v in all_villagers if v.location == "Cave" and v.steps_since_meal == 3)

        assigned = set()

        # PRIORITY 1: Eat villagers with meal >= 4 (MUST eat now to not starve)
        urgent = sorted([c for c in components if c.steps_since_meal >= 4],
                        key=lambda c: -c.steps_since_meal)
        wheat_used = 0
        for c in urgent:
            if wheat_used < wheat:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                wheat_used += 1
            # If no wheat, they'll starve - nothing we can do

        # PRIORITY 2: Send warriors to cave. Best candidates have meal 0 or 1.
        # Stagger: send at most 2 per step to maintain rotation.
        cave_warriors_count = sum(1 for v in environment.warriors if v.location == "Cave")
        cave_farmers_count = sum(1 for v in environment.farmers if v.location == "Cave")
        num_in_cave = cave_warriors_count + cave_farmers_count

        # Target 3-4 attackers in cave for good DPS
        if dragon_hp <= 15:
            target_cave = 6
        elif dragon_hp <= 40:
            target_cave = 4
        else:
            target_cave = 3
        # Don't exceed available warriors
        available_warriors = sum(1 for v in environment.warriors if v.location == "Village" and v.steps_since_meal <= 2 and v.hp >= 2)
        target_cave = min(target_cave, num_in_cave + available_warriors)

        need_to_send = max(0, target_cave - num_in_cave)

        remaining = [c for c in components if id(c) not in assigned]
        village_warriors = sorted(
            [c for c in remaining if c.role == "Warrior" and c.steps_since_meal <= 1 and c.hp >= 2],
            key=lambda c: c.steps_since_meal
        )

        # Stagger sending: at most 2 per step normally, more if cave is empty
        max_send = 2
        if num_in_cave == 0:
            max_send = max(2, need_to_send)

        sent = 0
        for w in village_warriors:
            if sent >= need_to_send or sent >= max_send:
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sent += 1

        # Desperation: if no attackers in cave and dragon is dangerous, send anyone ready
        if num_in_cave == 0 and sent == 0:
            desperate = sorted(
                [c for c in components if id(c) not in assigned and c.hp >= 2 and c.steps_since_meal <= 2],
                key=lambda c: (c.role != "Warrior", c.steps_since_meal)
            )
            for c in desperate[:2]:
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                sent += 1

        # PRIORITY 3: Spawn warriors when we have plenty of wheat
        # Reserve: wheat - meals_now - future mandatory meals should be >= spawn cost + buffer
        meals_now = wheat_used
        # Future mandatory meals next step: cave at meal 4 (cave_must_eat_next) +
        # village villagers at meal 3 who won't eat (we'll let them eat next step) +
        # village villagers at meal >= 4 who couldn't eat now
        unable_to_eat_now = sum(1 for c in urgent if id(c) not in assigned)
        village_meal3 = sum(1 for c in components if c.steps_since_meal == 3 and id(c) not in assigned)
        future_mandatory = cave_must_eat_next + unable_to_eat_now + village_meal3

        # Estimate farming output this step
        still_free = [c for c in components if id(c) not in assigned and c.steps_since_meal <= 3]
        farm_output = sum(5 if c.role == "Farmer" else 2 for c in still_free)

        wheat_after = wheat - meals_now + farm_output
        # Need at least future_mandatory + buffer for after spawn
        can_afford_spawn = wheat_after >= 12 + future_mandatory + 4
        total_warriors = len(environment.warriors)
        can_spawn = can_afford_spawn and len(remaining) >= 4 and total_warriors < 10

        if can_spawn:
            # Prefer using farmers for spawning (preserve warriors for attack)
            farmers_free = [c for c in components if id(c) not in assigned and c.role == "Farmer" and c.steps_since_meal <= 2]
            others_free = [c for c in components if id(c) not in assigned and c.role != "Farmer" and c.steps_since_meal <= 2]
            pool = farmers_free[:2] + others_free
            pool = pool[:2]
            if len(pool) == 2:
                for s in pool:
                    environment.assign_group(s, "spawn warrior")
                    assigned.add(id(s))

        # PRIORITY 4: Eat villagers with meal == 3 if we have surplus wheat
        # (preventive - reduces future mandatory eat pressure)
        wheat_after_spawn = wheat - meals_now  # approximate
        # Count farmers still farming to estimate input; this is rough
        # Be cautious: only eat at meal 3 if we have lots of wheat
        if wheat > meals_now + future_mandatory + 8:
            for c in components:
                if id(c) in assigned:
                    continue
                if c.steps_since_meal == 3:
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))

        # PRIORITY 5: Everyone remaining farms
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        assigned = set()

        # Sort: most hungry first so we decide returners first
        sorted_comps = sorted(components, key=lambda c: -c.steps_since_meal)

        # How many are currently attackers that we'll keep?
        keep_attacking = 0
        for c in sorted_comps:
            if id(c) in assigned:
                continue

            # MUST return at meal >= 4 (constraint: 1 step travel, arrive at 5, eat at 6 = starvation)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Return if dying (hp <= 1) and dragon not nearly dead
            if c.hp <= 1 and dragon_hp > 10:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Attack
            environment.assign_group(c, "attack")
            assigned.add(id(c))
            keep_attacking += 1

        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```