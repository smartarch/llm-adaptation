

## Strategy Description

The core problem is **insufficient sustained DPS**. With the dragon regenerating 5 HP/step when unattacked, I need continuous coverage. The optimal warrior rotation is: Eat(1) → Travel(1) → Attack(3) → Travel(1) = 6-step cycle with 50% uptime. With only 2-3 warriors, there are gaps where nobody attacks and the dragon heals.

**Key fixes:**
1. **Much more aggressive spawning**: Spawn a warrior EVERY step while wheat allows, using 2 farmers (who produce 0 wheat that step but produce 10 wheat next step - net gain after spawn).
2. **All warriors to cave immediately**: No warrior stays in village unless they need to eat. Even at s_m=0 in village, travel to cave immediately.
3. **Minimal farmers**: Only keep 2 farmers in village. Surplus farmers go to cave for late-game damage.
4. **Strict cave exit at s_m=4**: This is non-negotiable (prevents starvation).
5. **Stagger naturally**: Warriors naturally stagger because they eat at different steps. With 4+ warriors, coverage becomes continuous.

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
        total_warriors = len(all_warriors)
        total_villagers = total_warriors + len(all_farmers)

        # --- Categorize by hunger ---
        # Feed those at s_m >= 3 (must eat within 2 steps to be safe)
        hungry = [c for c in components if c.steps_since_meal >= 3]
        hungry.sort(key=lambda c: c.steps_since_meal, reverse=True)
        ok = [c for c in components if c.steps_since_meal < 3]

        wheat_left = wheat

        # Feed hungry villagers
        for c in hungry:
            if wheat_left > 0:
                environment.assign_group(c, "eat")
                wheat_left -= 1
            else:
                # No wheat - must farm (even if hungry, produce food first)
                environment.assign_group(c, "farm")

        # Remaining non-hungry villagers separated by role
        rem_farmers = [c for c in ok if c.role == "Farmer"]
        rem_warriors = [c for c in ok if c.role == "Warrior"]

        # --- Estimate wheat reserve for upcoming meals ---
        # Count villagers who will need food in next 1-2 steps
        need_eat_soon = 0
        for w in all_warriors:
            if w.location == "Cave" and w.steps_since_meal >= 2:
                need_eat_soon += 1
        for f in all_farmers:
            if f.location == "Cave" and f.steps_since_meal >= 2:
                need_eat_soon += 1
        for c in ok:
            if c.steps_since_meal >= 1:
                need_eat_soon += 1
        # Also villagers in village that are hungry but couldn't eat (no wheat)
        for c in hungry:
            if wheat <= 0:
                need_eat_soon += 1

        # Reserve wheat for meals
        reserve = max(need_eat_soon, 2)
        spawn_wheat = max(0, wheat_left - reserve)

        # --- SPAWNING: extremely aggressive ---
        # Priority 1: No warriors at all - CRITICAL, spawn immediately
        if total_warriors == 0 and spawn_wheat >= 12 and (len(rem_farmers) + len(rem_warriors)) >= 2:
            pool = rem_farmers + rem_warriors
            environment.assign_group(pool[0], "spawn warrior")
            environment.assign_group(pool[1], "spawn warrior")
            spawn_wheat -= 12
            used = {id(pool[0]), id(pool[1])}
            rem_farmers = [c for c in rem_farmers if id(c) not in used]
            rem_warriors = [c for c in rem_warriors if id(c) not in used]

        # Priority 2: Build up to 5-6 warriors fast
        elif total_warriors < 5 and spawn_wheat >= 12:
            if len(rem_farmers) >= 2:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_farmers[1], "spawn warrior")
                spawn_wheat -= 12
                rem_farmers = rem_farmers[2:]
            elif len(rem_farmers) >= 1 and len(rem_warriors) >= 1:
                environment.assign_group(rem_farmers[0], "spawn warrior")
                environment.assign_group(rem_warriors[0], "spawn warrior")
                spawn_wheat -= 12
                rem_farmers = rem_farmers[1:]
                rem_warriors = rem_warriors[1:]
            elif len(rem_warriors) >= 2:
                environment.assign_group(rem_warriors[0], "spawn warrior")
                environment.assign_group(rem_warriors[1], "spawn warrior")
                spawn_wheat -= 12
                rem_warriors = rem_warriors[2:]

        # Priority 3: Maintain warrior count (replace dead ones)
        elif total_warriors < 3 and spawn_wheat >= 12:
            pool = rem_farmers + rem_warriors
            if len(pool) >= 2:
                environment.assign_group(pool[0], "spawn warrior")
                environment.assign_group(pool[1], "spawn warrior")
                spawn_wheat -= 12
                used = {id(pool[0]), id(pool[1])}
                rem_farmers = [c for c in rem_farmers if id(c) not in used]
                rem_warriors = [c for c in rem_warriors if id(c) not in used]

        # --- SEND WARRIORS TO CAVE IMMEDIATELY ---
        # Warriors in village with s_m < 3 should go to cave NOW (they'll be fresh)
        for w in rem_warriors:
            environment.assign_group(w, "cave")

        # --- ASSIGN FARMERS ---
        # Keep minimum 2 farmers for wheat. Surplus goes to cave in mid/late game.
        num_farmers = len(rem_farmers)
        min_farm = 2 if num_farmers >= 2 else 1

        for i, f in enumerate(rem_farmers):
            if i < min_farm:
                environment.assign_group(f, "farm")
            elif dragon_hp <= 40:
                # Mid/late game: surplus farmers go to cave for extra damage
                environment.assign_group(f, "cave")
            else:
                # Early game: farm to build wheat surplus for spawning
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            s_m = c.steps_since_meal

            if s_m >= 4:
                # HARD LIMIT: must leave now.
                # Travel takes 1 step → arrive village at s_m=5 → eat next step.
                # If they stay, s_m hits 6 → starvation.
                environment.assign_group(c, "village")
            else:
                # s_m in [0,1,2,3]: safe to attack
                # After attack: s_m becomes 1,2,3,4 respectively.
                # At s_m=4 next step, they'll go to village. All safe.
                environment.assign_group(c, "attack")
```