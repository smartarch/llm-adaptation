

Looking at this problem, I need to design a strategy that:
1. Builds up warriors efficiently using wheat production
2. Maintains continuous dragon attacks (preventing 5 HP/step regen)
3. Manages the eat cycle (villagers must eat within 6 steps)
4. Staggered attack/eat cycles ensure someone always attacks

**Strategy:**
- **Economy phase:** Keep minimum farmers producing wheat, spawn warriors ASAP
- **Attack phase:** Warriors go to cave, attack in staggered waves (~3-4 attacks before returning to eat)
- **Food management:** Villagers with `steps_since_meal >= 4` get sent back to eat (safe buffer before starvation at 6)
- **Continuous coverage:** By staggering eat cycles, we ensure the dragon is always attacked (no regen)
- **Priority:** Attack > Eat > Farm > Spawn

The eat-move-attack cycle for warriors is roughly: Eat → Move(1) → Attack(2) → Attack(3) → Attack(4) → Move-back(5) → Eat, giving 3 attacks per ~6-step cycle. Staggering multiple warriors maintains continuous pressure.

```py
import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Separate components by priority
        # Priority 1: Must eat (steps_since_meal >= 4)
        eaters = [c for c in components if c.steps_since_meal >= 4]
        remaining = [c for c in components if c.steps_since_meal < 4]

        # Assign eaters
        for c in eaters:
            environment.assign_group(c, "eat")

        if not remaining:
            return

        # Count villagers in cave to estimate food demand
        villagers_in_cave = len([v for v in environment.warriors if v.location == "Cave"]) + \
                            len([v for v in environment.farmers if v.location == "Cave"])

        # Total villagers for food planning
        total_villagers = len(environment.farmers) + len(environment.warriors)

        # Minimum farmers needed to sustain wheat (each villager needs ~1 wheat/6 steps)
        # Farmer produces 5/step, Warrior produces 2/step in village
        min_farmers = max(1, math.ceil(total_villagers / 30))

        # Categorize remaining
        farmers_rem = [c for c in remaining if c.role == "Farmer"]
        warriors_rem = [c for c in remaining if c.role == "Warrior"]

        # Assign minimum farmers to farm
        farmers_farming = farmers_rem[:min_farmers]
        farmers_surplus = farmers_rem[min_farmers:]

        # Try to spawn warriors from surplus farmers (need 2 villagers + 12 wheat each)
        # Reserve wheat for upcoming meals
        wheat_reserve = max(villagers_in_cave, total_villagers // 2)
        available_wheat = max(0, wheat - wheat_reserve)
        max_spawnable = min(len(farmers_surplus) // 2, available_wheat // 12, 2)

        spawn_warrior_pool = farmers_surplus[:max_spawnable * 2]
        farmers_surplus = farmers_surplus[max_spawnable * 2:]

        for c in spawn_warrior_pool:
            environment.assign_group(c, "spawn warrior")

        # Determine how many farmers to send to cave vs farm
        # Send farmers to cave only if dragon HP is low or we have excess
        # Warriors always go to cave
        warriors_to_cave = []
        warriors_to_farm = []

        # Early game (dragon still high HP): focus on building army
        # Later game: send everyone to attack
        num_warriors_in_cave = len([v for v in environment.warriors if v.location == "Cave"])

        for c in warriors_rem:
            # Send warriors to cave unless they'll starve too soon
            if c.steps_since_meal <= 3:
                warriors_to_cave.append(c)
            else:
                warriors_to_farm.append(c)

        for c in warriors_to_cave:
            environment.assign_group(c, "cave")
        for c in warriors_to_farm:
            environment.assign_group(c, "farm")

        # Farmers farming (minimum)
        for c in farmers_farming:
            environment.assign_group(c, "farm")

        # Surplus farmers: farm for wheat, or send to cave if late game / dragon low
        # Keep producing wheat to sustain warriors in cave
        if dragon_hp < 20 and len(warriors_to_cave) + num_warriors_in_cave >= 3:
            # Close to killing dragon, send extra farmers to attack
            for c in farmers_surplus:
                if c.steps_since_meal <= 3:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "eat")
        else:
            # Keep farming for economy
            for c in farmers_surplus:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        # Separate by food urgency
        # Must go back to eat (steps_since_meal >= 4)
        need_food = [c for c in components if c.steps_since_meal >= 4]
        can_stay = [c for c in components if c.steps_since_meal < 4]

        # Assign those needing food back to village
        for c in need_food:
            environment.assign_group(c, "village")

        # Everyone else attacks (prevents dragon regen)
        # Even farmers should attack to prevent regen
        for c in can_stay:
            environment.assign_group(c, "attack")

        # Edge case: if nobody stays to attack, send one back and keep one attacking
        # (avoid dragon regen at all costs)
        # Actually if all are in need_food, one should stay to attack even if it means starving
        # But that's unlikely with staggered cycles. If it happens, the one with lowest
        # steps_since_meal should attack.
        if not can_stay and need_food:
            # Send the one with highest steps_since_meal back, keep one attacking
            need_food_sorted = sorted(need_food, key=lambda c: c.steps_since_meal, reverse=True)
            # Already assigned all to village above; reassign last one to attack
            keep_one = need_food_sorted[-1]  # lowest steps_since_meal
            # Unassign from village - can't unassign, so this won't work.
            # Instead, we should not assign the last one to village initially.
            pass  # Handled by logic: we already assigned all to village. 
            # This is a degenerate case that shouldn't happen with good staggering.
```

Wait, I realized there's a bug in the edge case handling. Let me fix the cave logic to properly handle the case where everyone needs food but someone must attack:

```py
import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Priority 1: Must eat (steps_since_meal >= 4)
        eaters = [c for c in components if c.steps_since_meal >= 4]
        remaining = [c for c in components if c.steps_since_meal < 4]

        for c in eaters:
            environment.assign_group(c, "eat")

        if not remaining:
            return

        # Food demand estimate
        villagers_in_cave = len([v for v in environment.warriors if v.location == "Cave"]) + \
                            len([v for v in environment.farmers if v.location == "Cave"])
        total_villagers = len(environment.farmers) + len(environment.warriors)
        min_farmers = max(1, math.ceil(total_villagers / 30))

        # Categorize remaining by role
        farmers_rem = [c for c in remaining if c.role == "Farmer"]
        warriors_rem = [c for c in remaining if c.role == "Warrior"]

        # Minimum farmers stay farming
        farmers_farming = farmers_rem[:min_farmers]
        farmers_surplus = farmers_rem[min_farmers:]

        # Spawn warriors from surplus if possible
        wheat_reserve = max(villagers_in_cave, 5)
        available_wheat = max(0, wheat - wheat_reserve)
        max_spawnable = min(len(farmers_surplus) // 2, available_wheat // 12, 2)

        spawn_pool = farmers_surplus[:max_spawnable * 2]
        farmers_surplus = farmers_surplus[max_spawnable * 2:]

        for c in spawn_pool:
            environment.assign_group(c, "spawn warrior")

        # Send warriors to cave
        for c in warriors_rem:
            environment.assign_group(c, "cave")

        # Minimum farmers farm
        for c in farmers_farming:
            environment.assign_group(c, "farm")

        # Surplus farmers: farm for wheat, or attack if dragon is nearly dead
        if dragon_hp <= 15:
            for c in farmers_surplus:
                environment.assign_group(c, "cave")
        else:
            for c in farmers_surplus:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        # Split: must go eat vs can keep attacking
        need_food = [c for c in components if c.steps_since_meal >= 4]
        can_stay = [c for c in components if c.steps_since_meal < 4]

        # CRITICAL: Always ensure at least one villager attacks to prevent regen
        # If everyone needs food, keep the one with lowest steps_since_meal attacking
        if not can_stay and need_food:
            # Sort by steps_since_meal; keep the freshest one to attack
            need_food_sorted = sorted(need_food, key=lambda c: c.steps_since_meal)
            keep_attacking = need_food_sorted[0]
            send_to_village = need_food_sorted[1:]

            for c in send_to_village:
                environment.assign_group(c, "village")
            environment.assign_group(keep_attacking, "attack")
        else:
            # Normal case: send hungry ones back, rest attack
            for c in need_food:
                environment.assign_group(c, "village")
            for c in can_stay:
                environment.assign_group(c, "attack")
```