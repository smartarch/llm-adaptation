

Looking at the failures carefully:

1. **Double assignment bug**: Components in `hungry_fresh` get assigned "farm" in one loop, then potentially re-processed in later logic. I need a single-pass assignment with tracking.

2. **Dragon not killed**: The critical insight is that **the dragon regenerates 5 HP/step when unattacked**. Even one farmer dealing 1 damage nets -4 HP, while zero attackers means +5 HP. So **never let the cave be empty** once the first attack happens. Also need more aggressive warrior spawning and better staggering.

**Strategy:**
- **Phase 1 (buildup)**: Spawn warriors ASAP from farmers. Send existing warriors to cave immediately. 
- **Phase 2 (sustained attack)**: Stagger warriors so ~4/7 are always attacking. Fill any gaps with farmers.
- **Phase 3 (endgame)**: Everyone rushes the cave.
- **Hunger**: Leave cave at s_m≥4 (arrive village s_m=5, eat → safe). 
- **Cave must never be empty after first attack** — send farmers as emergency attackers.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        num_warriors = len(environment.warriors)
        num_farmers = len(environment.farmers)
        total = num_warriors + num_farmers

        warriors_in_cave = sum(1 for w in environment.warriors if w.location == "Cave")
        farmers_in_cave = sum(1 for f in environment.farmers if f.location == "Cave")
        attackers_in_cave = warriors_in_cave + farmers_in_cave

        # Check if cave will have attackers next step (anyone in cave with s_m < 4)
        # will keep attacking. Those with s_m >= 4 are leaving.
        cave_will_have_attackers = False
        for w in environment.warriors:
            if w.location == "Cave" and w.steps_since_meal < 4:
                cave_will_have_attackers = True
                break
        if not cave_will_have_attackers:
            for f in environment.farmers:
                if f.location == "Cave" and f.steps_since_meal < 4:
                    cave_will_have_attackers = True
                    break

        # Track assignments to prevent double-assignment
        assigned_ids = set()
        def do_assign(comp, group):
            cid = id(comp)
            if cid not in assigned_ids:
                assigned_ids.add(cid)
                environment.assign_group(comp, group)

        # Endgame: everyone rushes cave
        if dragon_hp <= 25:
            for c in components:
                do_assign(c, "cave")
            return

        # Priority 1: Must eat (s_m >= 5)
        for c in components:
            if c.steps_since_meal >= 5:
                do_assign(c, "eat")

        # Priority 2: Hungry (s_m == 4) - eat now to be safe
        for c in components:
            if id(c) not in assigned_ids and c.steps_since_meal == 4:
                do_assign(c, "eat")

        # Remaining are fresh (s_m 0-3)
        remaining = [c for c in components if id(c) not in assigned_ids]
        fresh_farmers = [c for c in remaining if c.role == "Farmer"]
        fresh_warriors = [c for c in remaining if c.role == "Warrior"]

        # Sort warriors by role priority: those with s_m=0 go first (they can attack sooner)
        fresh_warriors.sort(key=lambda w: w.steps_since_meal)

        # Determine if we need backup attackers in cave
        need_backup_attackers = (attackers_in_cave == 0) and not cave_will_have_attackers

        # Allocate farmers: farming, spawning, or backup attack
        min_farm = 1  # always keep at least 1 farmer farming for wheat
        if total < 4:
            min_farm = 0  # very small population, can sacrifice farming

        farm_assigned = 0
        spawn_pool = []

        for f in fresh_farmers:
            if farm_assigned < min_farm:
                do_assign(f, "farm")
                farm_assigned += 1
            else:
                spawn_pool.append(f)

        # Spawn warriors aggressively
        reserve = max(total, 4)
        for i in range(0, len(spawn_pool) - 1, 2):
            if wheat >= 12 + reserve and (num_warriors < 8 or total < 5 or num_warriors == 0):
                do_assign(spawn_pool[i], "spawn warrior")
                do_assign(spawn_pool[i + 1], "spawn warrior")
                wheat -= 12
                num_warriors += 1
            else:
                do_assign(spawn_pool[i], "farm")
                do_assign(spawn_pool[i + 1], "farm")

        if len(spawn_pool) % 2 == 1:
            do_assign(spawn_pool[-1], "farm")

        # Send fresh warriors to cave (stagger if many)
        if len(fresh_warriors) >= 4:
            # Stagger: send half, keep half to farm (they'll go next step or after next meal)
            half = len(fresh_warriors) // 2
            for w in fresh_warriors[:half + 1]:
                do_assign(w, "cave")
            for w in fresh_warriors[half + 1:]:
                do_assign(w, "farm")
        else:
            for w in fresh_warriors:
                do_assign(w, "cave")

        # If cave has no attackers and won't next step, send farmers as backup
        if need_backup_attackers:
            for c in components:
                if id(c) not in assigned_ids and c.role == "Farmer":
                    do_assign(c, "cave")
                    break

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            # Endgame: attack regardless of hunger
            if dragon_hp <= 25:
                environment.assign_group(c, "attack")
            # About to starve: go to village NOW
            # s_m=4 in cave → arrive village with s_m=5 → eat next step (safe)
            elif c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```