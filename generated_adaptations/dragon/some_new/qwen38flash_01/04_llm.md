

## Strategy Analysis

The main issues with my previous solution:
1. **Dragon not killed**: Not enough sustained damage. Warriors weren't being sent to cave aggressively enough, and spawning was too restrictive.
2. **No warrior spawning when warriors=0**: The spawn group just needs ANY 2 villagers (not necessarily 2 warriors). Two farmers can spawn a warrior!
3. **Not spawning when <5 villagers**: The optional constraint hints we should aggressively grow population early.

**New Strategy:**
- **Aggressive spawning**: If no warriors exist, immediately use 2 farmers to spawn a warrior. If <5 villagers with enough wheat, keep spawning warriors.
- **Maximum attack pressure**: Send ALL warriors to cave and attack. Only retreat at s_m ≥ 5 (accept 1 HP starvation loss).
- **Minimal farming**: Just enough farmers to feed everyone. Surplus farmers go to cave in late game.
- **Feed priority**: Eat at s_m ≥ 4 in village to avoid starvation.

```py
import generated_adaptations.base_classes.dragon as base


class SmartAdaptation(base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        total_villagers = len(all_warriors) + len(all_farmers)
        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")

        # Categorize by hunger urgency
        urgent = [c for c in components if c.steps_since_meal >= 4]
        urgent.sort(key=lambda c: c.steps_since_meal, reverse=True)
        ok = [c for c in components if c.steps_since_meal < 4]

        assigned_ids = set()
        wheat_left = wheat

        # Feed urgent villagers (s_m >= 4)
        for c in urgent:
            if wheat_left > 0:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                # No wheat: if farmer, farm to produce; if warrior, farm too (produce 2)
                environment.assign_group(c, "farm")
            assigned_ids.add(id(c))

        # Remaining villagers (s_m < 4) - categorize by role
        remaining = [c for c in ok if id(c) not in assigned_ids]
        farmers_rem = [c for c in remaining if c.role == "Farmer"]
        warriors_rem = [c for c in remaining if c.role == "Warrior"]

        # --- SPAWNING LOGIC ---
        spawned_this_step = False

        # Critical: if no warriors exist at all, spawn one immediately
        if len(all_warriors) == 0 and wheat_left >= 12:
            pool = farmers_rem + warriors_rem
            if len(pool) >= 2:
                for c in pool[:2]:
                    environment.assign_group(c, "spawn warrior")
                    assigned_ids.add(id(c))
                wheat_left -= 12
                spawned_this_step = True
                # Remove spawned pool members
                spawn_ids = {id(pool[0]), id(pool[1])}
                farmers_rem = [c for c in farmers_rem if id(c) not in spawn_ids]
                warriors_rem = [c for c in warriors_rem if id(c) not in spawn_ids]

        # If < 5 total villagers and enough wheat, spawn a warrior
        if not spawned_this_step and total_villagers < 5 and wheat_left >= 12:
            pool = farmers_rem if len(farmers_rem) >= 2 else (
                warriors_rem if len(warriors_rem) >= 2 else [])
            if len(pool) >= 2:
                for c in pool[:2]:
                    environment.assign_group(c, "spawn warrior")
                    assigned_ids.add(id(c))
                wheat_left -= 12
                spawned_this_step = True
                spawn_ids = {id(pool[0]), id(pool[1])}
                farmers_rem = [c for c in farmers_rem if id(c) not in spawn_ids]
                warriors_rem = [c for c in warriors_rem if id(c) not in spawn_ids]

        # If we have lots of wheat and < 7 villagers, keep spawning
        if not spawned_this_step and total_villagers < 7 and wheat_left >= 20:
            pool = farmers_rem if len(farmers_rem) >= 2 else (
                warriors_rem if len(warriors_rem) >= 2 else [])
            if len(pool) >= 2:
                for c in pool[:2]:
                    environment.assign_group(c, "spawn warrior")
                    assigned_ids.add(id(c))
                wheat_left -= 12
                spawned_this_step = True
                spawn_ids = {id(pool[0]), id(pool[1])}
                farmers_rem = [c for c in farmers_rem if id(c) not in spawn_ids]
                warriors_rem = [c for c in warriors_rem if id(c) not in spawn_ids]

        # --- ASSIGN WAR