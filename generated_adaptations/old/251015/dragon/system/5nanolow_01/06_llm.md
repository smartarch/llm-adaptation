Reasoning and improved strategy:
- Core goal: maximize near-term DPS while ensuring growth to sustain the pressure on the Dragon.
- Key constraints:
  - All Warriors should go to the Cave to attack the Dragon.
  - Farmers stay in the Village and can either farm (to generate more wheat) or participate in spawning events to create new villagers.
  - Spawning requires exact resource-cost per two villagers: 10 wheat for a new Farmer, 12 wheat for a new Warrior.
  - The spawn groups trigger only when exactly two villagers are assigned to that group and enough wheat is available.
- Improved approach:
  - In the village, first allocate as many farmer-spawns as possible using the current wheat to seed population growth (pf pairs). This aggressively expands the workforce to sustain longer campaigns.
  - After allocating farmer-spawns, use any remaining farmers to form warrior-spawns only if there is sufficient wheat left to cover both the two-villager requirement and its wheat cost (pw pairs). This keeps a bias toward growth when wheat permits.
  - The rest of the farmers stay in the village in the farm group to keep producing wheat.
  - In the cave, keep Warriors in the attack group and move Farmers to cave only as a safe fallback (though per the rule, all Warriors should attack and Farmers should stay in Village; the fallback ensures graceful handling if a Farmer ends up in the cave).
- Rationale: This approach emphasizes early growth when wheat is available, ensuring a larger farming force to sustain spawning later. By keeping Warriors in the cave for immediate damage, we still maintain DPS while avoiding stalling the Dragon with non-attacking villagers.

Code (updated SmartAdaptation implementation):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Improved strategy:
        # - All Warriors: send to cave (attack) if in village context we still funnel them to cave.
        # - All Farmers: allocate to spawning as much as possible given farm wheat, then remaining to farm.
        #   pf = number of farmer-spawn pairs
        #   pw = number of warrior-spawn pairs (if wheat permits after farmer-spawns)
        group_for_assign = {group: [] for group in group_ids}

        # Classify villagers in village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Defensive: if any warriors are unexpectedly in village, send them to cave
        for w in warriors:
            group_for_assign["cave"].append(w)

        # Wheat available at Farm
        wheat = getattr(environment.farm, "wheat", 0)

        F = len(farmers)
        # Pairs for spawning farmers
        pf = min(F // 2, wheat // 10)
        k_farm_spawn = 2 * pf
        wheat -= pf * 10

        # Remaining farmers after farmer-spawns
        remaining_after_pf = F - k_farm_spawn

        # Pairs for spawning warriors with remaining wheat
        pw = min(remaining_after_pf // 2, wheat // 12) if wheat >= 12 else 0
        k_war_spawn = 2 * pw
        wheat -= pw * 12

        # Allocate farmers to groups accordingly
        if k_farm_spawn > 0:
            for f in farmers[:k_farm_spawn]:
                group_for_assign["spawn farmer"].append(f)

        if k_war_spawn > 0:
            for f in farmers[k_farm_spawn:k_farm_spawn + k_war_spawn]:
                group_for_assign["spawn warrior"].append(f)

        remaining_farmers = farmers[k_farm_spawn + k_war_spawn:]
        for f in remaining_farmers:
            group_for_assign["farm"].append(f)

        # Fallback: ensure all components are assigned
        assigned = []
        for lst in group_for_assign.values():
            assigned.extend(lst)
        unassigned = [c for c in components if c not in assigned]
        for c in unassigned:
            group_for_assign["farm"].append(c)

        # Apply assignments
        for gid, lst in group_for_assign.items():
            for c in lst:
                environment.assign_group(c, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy: Warriors attack; Farmers stay in cave as a safe fallback (prefer to keep them in cave if they land here)
        group_for_assign = {group: [] for group in group_ids}

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                group_for_assign["attack"].append(c)
            elif role == "Farmer":
                group_for_assign["cave"].append(c)
            else:
                group_for_assign["cave"].append(c)

        for gid, lst in group_for_assign.items():
            for c in lst:
                environment.assign_group(c, gid)
```