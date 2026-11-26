

# Adaptation Strategy for Dragon Hunt

## Strategy Overview

The strategy has two phases:
1. **Build-up phase**: Farmers produce wheat, and we spawn warriors (high DPS). Once we have enough warriors to sustain a continuous attack cycle (accounting for eating rotations), we begin the assault.
2. **Assault phase**: Warriors rotate between cave (attacking) and village (eating) in staggered cycles, ensuring the dragon is attacked every step (preventing its 5 HP/step regeneration).

**Key considerations:**
- Villagers must eat within 5 steps (steps_since_meal < 6). We send villagers back to village at threshold 4 (in cave) or 5 (in village) to avoid starvation damage.
- The rotation cycle takes 3 steps (move→eat→move), so warriors attack for ~5 of every 8 steps. With staggering, we maintain continuous attack coverage.
- We prioritize spawning warriors (3 dmg) over farmers (1 dmg) for attacking, while maintaining enough farmers for wheat production.
- If the dragon is nearly dead, we push all available villagers to attack despite starvation risk.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attack_started = False
        self.warriors_in_cave = 0
        self.total_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)
        total_villagers = total_warriors + total_farmers

        # Count villagers in cave
        warriors_in_cave = sum(1 for w in environment.warriors if w.location == "Cave")
        farmers_in_cave = sum(1 for f in environment.farmers if f.location == "Cave")
        attackers_in_cave = warriors_in_cave + farmers_in_cave

        # Determine if we should push everyone to cave (dragon nearly dead)
        dragon_low = dragon_hp <= 15 and attackers_in_cave > 0

        # Categorize villagers by hunger urgency
        must_eat = []        # steps_since_meal >= 5: MUST eat this step
        eat_soon = []        # steps_since_meal >= 3: should eat soon
        fresh = []           # steps_since_meal < 3: free to act

        for comp in components:
            if comp.steps_since_meal >= 5:
                must_eat.append(comp)
            elif comp.steps_since_meal >= 3:
                eat_soon.append(comp)
            else:
                fresh.append(comp)

        # 1) Must eat: assign to "eat"
        for v in must_eat:
            environment.assign_group(v, "eat")

        # 2) Eat soon (steps 3-4): eat to be safe, except if dragon is nearly dead
        for v in eat_soon:
            if dragon_low and v.role == "Warrior":
                # Risk it - send to cave to deal damage
                environment.assign_group(v, "cave")
            elif v.steps_since_meal >= 4:
                environment.assign_group(v, "eat")
            else:
                # steps 3, can still do one more productive step
                if v.role == "Farmer":
                    environment.assign_group(v, "farm")
                else:
                    environment.assign_group(v, "farm")  # farm 1 more step then eat

        # 3) Fresh villagers: decide their assignment
        # Need enough farmers farming to sustain the population
        # Each villager eats 1 wheat per 6 steps; each farmer farms produces 5/step
        # Min farmers farming needed: ceil(total_villagers / 30) ≈ 1-2 for small populations
        min_farmers_farming = max(1, total_villagers // 8 + 1)

        fresh_farmers = [v for v in fresh if v.role == "Farmer"]
        fresh_warriors = [v for v in fresh if v.role == "Warrior"]

        # Assign farmers: farm or spawn warriors
        farmers_farming_count = 0
        spawn_pool = []

        for i, v in enumerate(fresh_farmers):
            if farmers_farming_count < min_farmers_farming:
                environment.assign_group(v, "farm")
                farmers_farming_count += 1
            else:
                spawn_pool.append(v)

        # Spawn warriors from excess farmers (pairs of 2, costs 12 wheat)
        # But keep at least min_farmers_farming total farmers actively farming
        # (count already assigned above)
        spawnable_pairs = len(spawn_pool) // 2
        # Check if wheat can sustain spawns
        # Also check if we have enough farmers still farming after this
        remaining_farming = farmers_farming_count
        for i in range(0, len(spawn_pool) - 1, 2):
            if wheat >= 12 and remaining_farming >= 1:
                environment.assign_group(spawn_pool[i], "spawn warrior")
                environment.assign_group(spawn_pool[i + 1], "spawn warrior")
                remaining_farming -= 2  # they're now in spawn group
                self.total_spawned += 1
            else:
                # Send them to farm instead
                environment.assign_group(spawn_pool[i], "farm")
                if i + 1 < len(spawn_pool):
                    environment.assign_group(spawn_pool[i + 1], "farm")

        # Handle odd leftover in spawn_pool
        if len(spawn_pool) % 2 == 1:
            environment.assign_group(spawn_pool[-1], "farm")

        # Assign fresh warriors: send to cave to attack
        for v in fresh_warriors:
            environment.assign_group(v, "cave")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        # If dragon is nearly dead, everyone attacks regardless of hunger
        # 100 HP / (3 dmg/warrior) ≈ need all available DPS
        dragon_low = dragon_hp <= 20

        for comp in components:
            if dragon_low:
                # All-out assault: everyone attacks even if starving
                environment.assign_group(comp, "attack")
            elif comp.steps_since_meal >= 4:
                # About to starve: go back to village to eat
                # At step 4, move → arrive with 5 → eat next step (safe)
                environment.assign_group(comp, "village")
            else:
                # Safe to attack
                environment.assign_group(comp, "attack")
```