

Looking at the persistent 0% win rate, I need to rethink fundamentally.

**Critical insight about game mechanics:**
- Dragon regen (5 HP/step) ONLY happens when NOBODY attacks that step. So I just need at least 1 attacker every step, not heavy coverage.
- Each warrior gets exactly **2 attacks per 6-step cycle** (eat → travel → attack → attack → travel → eat). To never have an empty step, need 3 warriors perfectly staggered at offsets 0, 2, 4.
- With 3 warriors: 3 dmg/step, no regen → 34 steps (too slow!). Need more.
- With 6 warriors: 6 dmg/step → 17 steps. With 9: 9 dmg/step → 11 steps.
- So I must spawn warriors FAST (each costs 12 wheat + 2 villagers) while keeping wheat for eating.

**Why previous attempts failed:** My rotation logic was overly cautious about `steps_since_meal`, often refusing to send warriors who could still get 2 attacks. The cave frequently became empty, causing regen to outpace damage.

**New strategy — aggressive, simple, and correct:**
- Always send warriors with `steps_since_meal ≤ 2` to cave if it would be empty (or near empty) next step.
- Send up to 3 at once when cave is undermanned to build the rotation.
- Spawn warriors whenever wheat surplus ≥ 16 (covers 12 spawn + 4 buffer).
- Eat at `meal ≥ 4` (mandatory). Optional eat at 3 only if massive surplus.
- In cave: return only at `meal ≥ 4` or `hp ≤ 1`. Attack otherwise — never idle in cave.
- Track incoming sends so we don't over-stuff the cave.

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
        assigned = set()
        meals_used = 0

        # Estimate how many will be attacking in cave NEXT step
        # (current cave dwellers who aren't leaving)
        will_attack_next = sum(
            1 for v in all_villagers
            if v.location == "Cave" and v.steps_since_meal <= 2
        )

        # ===== 1. MANDATORY EAT (meal >= 4) =====
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if c.steps_since_meal >= 4:
                if meals_used < wheat:
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))
                    meals_used += 1
                else:
                    # No wheat — they will starve; assign farm (can't do better)
                    environment.assign_group(c, "farm")
                    assigned.add(id(c))

        # ===== 2. SEND WARRIORS TO CAVE (maintain rotation) =====
        # Target: 3+ attackers in cave next step ideally; minimum 1 always
        target = 3 if dragon_hp > 25 else 5
        need_to_send = max(0, target - will_attack_next)

        # Candidates: warriors with meal <= 2 (guarantees 2 attacks this trip)
        send_pool = sorted(
            [c for c in components
             if id(c) not in assigned
             and c.role == "Warrior"
             and c.steps_since_meal <= 2
             and c.hp >= 2],
            key=lambda c: c.steps_since_meal
        )

        # If cave will be empty, send up to 3 at once to bootstrap rotation
        max_batch = 3 if will_attack_next == 0 else 2
        sent = 0
        for w in send_pool:
            if sent >= need_to_send or sent >= max_batch:
                break
            environment.assign_group(w, "cave")
            assigned.add(id(w))
            sent += 1

        # Emergency: cave empty, no warriors qualified — send farmers
        if will_attack_next == 0 and sent == 0:
            emergency = sorted(
                [c for c in components
                 if id(c) not in assigned and c.steps_since_meal <= 2 and c.hp >= 2],
                key=lambda c: (c.role == "Farmer", c.steps_since_meal)
            )
            for c in emergency[:2]:
                environment.assign_group(c, "cave")
                assigned.add(id(c))
                sent += 1

        # ===== 3. SPAWN WARRIORS aggressively =====
        remaining = [c for c in components if id(c) not in assigned]
        total_warriors = len(environment.warriors)
        # Reserve wheat for villagers currently at meal=3 (they'll need to eat within 2 steps)
        upcoming_meals = sum(
            1 for c in components if c.steps_since_meal == 3 and id(c) not in assigned
        ) + sum(1 for v in all_villagers if v.location == "Cave" and v.steps_since_meal >= 3)
        # Estimate farming output from villagers still assigned to farm this step
        farm_out = sum(
            5 if c.role == "Farmer" else 2
            for c in remaining if c.steps_since_meal <= 3
        )
        projected = wheat - meals_used + farm_out
        # Need 12 for spawn + upcoming meals buffer
        if projected >= 12 + upcoming_meals + 2 and len(remaining) >= 4 and total_warriors < 10:
            # Prefer using farmers for spawn (preserve warriors for attack)
            pool = sorted(remaining, key=lambda c: (c.role == "Warrior", c.steps_since_meal))
            if len(pool) >= 2:
                environment.assign_group(pool[0], "spawn warrior")
                assigned.add(id(pool[0]))
                environment.assign_group(pool[1], "spawn warrior")
                assigned.add(id(pool[1]))

        # ===== 4. Optional preventive eat at meal=3 if abundant =====
        if wheat - meals_used >= 8:
            for c in components:
                if id(c) in assigned:
                    continue
                if c.steps_since_meal == 3 and c.role == "Farmer":
                    environment.assign_group(c, "eat")
                    assigned.add(id(c))
                    meals_used += 1
                    break

        # ===== 5. Everything remaining farms =====
        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        assigned = set()

        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue

            # MUST leave cave at meal >= 4 (would starve otherwise)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Leave if dying
            if c.hp <= 1:
                environment.assign_group(c, "village")
                assigned.add(id(c))
                continue

            # Otherwise: attack the dragon (always — never idle, idle = regen)
            environment.assign_group(c, "attack")
            assigned.add(id(c))

        for c in components:
            if id(c) not in assigned:
                environment.assign_group(c, "attack")
```