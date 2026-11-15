The 21.0 run regressed because burst multi-spawning drained wheat for meals and income. I'm returning to a **sustained one-pair-per-step** spawn model (which produced 19.7), but improving it on the two things that matter most for kill speed:

1. **Regeneration is the real enemy.** 5 HP/turn regen exceeds one warrior's 3 damage, so any unattacked turn is a net loss. Warriors spawned every step are *naturally age-staggered* (a turn-T spawn is always `step − T` steps since its meal), so continuous spawning keeps somebody in the attack window (`steps_since_meal ≤ 5`) nearly every turn, preventing regen without an explicit schedule.
2. **Slightly better economy:** ramp to ~3 farmers (rather than stopping at 2) so wheat income can *sustain* one warrior-pair spawn per step for the whole game, while still protecting at least one farming farmer and always prioritizing meals over spawning.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        assigned = {}
        budget = max(0, int(getattr(environment.farm, "wheat", 0)))

        farmers = [c for c in comps if c.role == "Farmer"]
        warriors = [c for c in comps if c.role == "Warrior"]

        # ---- 1. Meals (always the top priority: stay alive & avoid starving) ----
        # Anyone at 5+ must eat; warriors must eat at 3+ before they can be sent
        # to the Cave (they would otherwise have to turn back before attacking).
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c in assigned:
                continue
            must_eat = c.steps_since_meal >= 5
            warrior_pre_eat = (c.role == "Warrior" and c.steps_since_meal >= 3)
            if (must_eat or warrior_pre_eat) and budget > 0:
                assigned[c] = "eat"
                budget -= 1

        # ---- 2. Warriors in the Village ----
        # Fresh warriors go straight to the Cave so they attack almost at once.
        for w in warriors:
            if w in assigned:
                continue
            if w.steps_since_meal < 3 and w.hp > 0:
                assigned[w] = "cave"
            else:
                assigned[w] = "farm"  # waiting to be fed on a later step

        # ---- 3. Farmers: grow to a small base, then feed a steady warrior stream ----
        free_farmers = [f for f in farmers if f not in assigned]
        free_farmers.sort(key=lambda x: x.steps_since_meal)
        n_farmers = len(farmers)

        # Never stop all farming: keep at least one to fund wheat income.
        keep_farming = 1 if n_farmers >= 2 else 0
        max_spawn_pairs = max(0, (len(free_farmers) - keep_farming)) // 2

        FARMER_TARGET = 3
        idx = 0

        # Farmer spawn: at most one pair per step, until the base is reached.
        if n_farmers < FARMER_TARGET and max_spawn_pairs >= 1 and budget >= 10:
            assigned[free_farmers[idx]] = "spawn farmer"
            assigned[free_farmers[idx + 1]] = "spawn farmer"
            idx += 2
            budget -= 10
            max_spawn_pairs -= 1

        # Warrior spawn: one pair per step (sustained, avoids draining wheat).
        if max_spawn_pairs >= 1 and budget >= 12:
            assigned[free_farmers[idx]] = "spawn warrior"
            assigned[free_farmers[idx + 1]] = "spawn warrior"
            idx += 2
            budget -= 12

        # Everyone else farms.
        for f in free_farmers[idx:]:
            assigned[f] = "farm"

        # ---- Safety net + apply ----
        for c in comps:
            if c not in assigned:
                assigned[c] = "farm" if c.role == "Farmer" else "cave"
            environment.assign_group(c, assigned[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        comps = list(components)
        for c in comps:
            # Attack for the full window in which we still deal damage
            # (starving / no-damage starts only once steps_since_meal reaches 6).
            # Otherwise travel home so the villager can eat.
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= 5:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```