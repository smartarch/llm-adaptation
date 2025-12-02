Reasoning and adaptation strategy:
- Observed bottleneck: To win, we need to deliver rapid DPS to the Dragon while keeping villagers alive long enough to sustain farming and spawning. Spawns cost wheat and use two villagers, so we should spawn aggressively early to flood the village with more fighters/harvesters, but do so in a way that preserves wheat production for future spawns.
- Core idea of the improved strategy:
  - Warriors (attackers) stay in the Cave to attack the Dragon; all Warriors should be in the cave as soon as possible to maximize early damage.
  - Farmers stay in the Village to farm wheat. Wheat is the bottleneck for spawning new villagers.
  - Spawn greedily in the village whenever there is enough wheat:
    - First, spawn as many farmers as possible (two farmers per spawn, cost 10 wheat each).
    - Then, using the remaining wheat, spawn as many warriors as possible (two farmers per spawn, cost 12 wheat each).
  - This approach ensures early population growth and rapid DPS, while still preserving wheat production by keeping non-spawn farmers in the farm pool for ongoing wheat generation.
  - All components are assigned exactly once per step; no repeated assignments.
- Implementation notes:
  - We initialize final_group with Warriors → cave and Farmers → farm.
  - We greedily allocate two-villager pairs to spawn farmer until we run out of wheat or eligible farmers in farm.
  - We then allocate two-villager pairs to spawn warrior from remaining farmers in farm.
  - Finally, we apply all final assignments to the environment, ensuring deterministic, single-assignment per component.
  - assign_in_cave remains straightforward: Warriors → attack, Farmers → village.

Code (Python, single code block):

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a final assignment map for this step
        final_group = {}

        # Base rule: Warriors go to cave (to attack), Farmers stay in farm
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                final_group[c] = "cave"
            else:
                final_group[c] = "farm"

        # Wheat currently available in the Farm
        remaining_wheat = getattr(environment.farm, "wheat", 0)

        # Lists for convenience
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]

        # Farmers currently in Farm (eligible for spawning a farmer)
        farm_candidates = [c for c in farmers if final_group.get(c) == "farm"]

        # Spawn Farmers: need two villagers and 10 wheat
        sp_farm_candidates = list(farm_candidates)
        while len(sp_farm_candidates) >= 2 and remaining_wheat >= 10:
            a = sp_farm_candidates.pop(0)
            b = sp_farm_candidates.pop(0)
            final_group[a] = "spawn farmer"
            final_group[b] = "spawn farmer"
            remaining_wheat -= 10

        # Spawn Warriors: use remaining farmers not already spawning as farmers
        sp_war_candidates = [c for c in farmers if final_group.get(c) == "farm"]
        # Exclude those already allocated to spawn farmer
        sp_farmed = {c for c, g in final_group.items() if g == "spawn farmer"}
        sp_war_candidates = [c for c in sp_war_candidates if c not in sp_farmed]

        while len(sp_war_candidates) >= 2 and remaining_wheat >= 12:
            a = sp_war_candidates.pop(0)
            b = sp_war_candidates.pop(0)
            final_group[a] = "spawn warrior"
            final_group[b] = "spawn warrior"
            remaining_wheat -= 12

        # Apply final assignments (each component assigned exactly once)
        for comp, grp in final_group.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            if getattr(comp, "role", "") == "Warrior":
                grp = "attack"
            else:
                grp = "village"
            environment.assign_group(comp, grp)
```