Reasoning and updated strategy

Summary of what to change:
- The core difficulty is delivering enough Dragon DPS early while keeping villagers alive and growing the force through spawning. Previous attempts moved all Warriors to the Cave in one go, which increases early DPS but risks large casualties from Dragon counter-attacks and may underutilize wheat for rapid population growth.
- The new approach uses a staged, step-aware escalation:
  - In village phase, gradually move Warriors to the Cave: up to 2 per step, so by step 0 you have some attackers and by step 1–2 you can have more, increasing DPS without overwhelming the Dragon with counter-attacks early.
  - Spawn farming and warrior spores in a budget-aware way each step:
    - Use wheat to spawn Farmer pairs (2 Farmers per spawn, 10 wheat per spawn) to grow wheat production.
    - After allocating Farmer spawns, use remaining wheat and remaining Farmers to spawn Warrior pairs (2 Farmers per spawn, 12 wheat per spawn) to boost DPS, ensuring a steady growth of both populations.
  - Farmers remain in the Village for farming/spawning; Warriors eventually move to Cave to attack.
- This staged escalation aims to ensure:
  - The Dragon is attacked early (by step 0–2) with a growing force.
  - Population grows in parallel with wheat production, enabling more DPS in later steps.
  - Casualties are controlled by not flooding the Cave with warriors too aggressively too early.

Implementation notes:
- In assign_in_village, we now move at most 2 Warriors to the Cave per step (subject to availability). The rest of the Warriors stay in the Village this step for potential spawning of more troops in future steps.
- We keep the per-step, budgeted spawning logic, respecting the constraint that 2 Farmers are required for every Farmer spawn and 2 Farmers are required for every Warrior spawn, along with the Wheat costs (10 and 12 respectively).
- In assign_in_cave, Warriors attack and Farmers return to the Village.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Staged assault: gradually move Warriors to the Cave (max 2 per step),
        # while aggressively spawning Farmers and Warriors based on wheat.
        if not components:
            return

        # Separate by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move Warriors to the Cave gradually: up to 2 per step
        move_limit = min(2, len(warriors))
        for i in range(move_limit):
            environment.assign_group(warriors[i], "cave")

        # 2) Keep remaining Farmers in Village by default (farm)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Aggressive, budgeted spawning (per-step)
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmer spawns: need 2 farmers and 10 wheat per spawn
        n_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Trigger farmer spawns using disjoint farmer pairs
        for i in range(n_farm_spawns):
            c1 = farmers[2 * i]
            c2 = farmers[2 * i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")

        # Update wheat budget after farmer spawns
        wheat_after_farm = wheat - n_farm_spawns * 10
        idx_after_farm = 2 * n_farm_spawns

        remaining_farmers_for_war = len(farmers) - idx_after_farm

        # Warrior spawns: need 2 farmers and 12 wheat per spawn
        n_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)

        # Trigger warrior spawns using disjoint farmer pairs after farmers for farmer-spawns
        for i in range(n_war_spawns):
            c1 = farmers[idx_after_farm + 2 * i]
            c2 = farmers[idx_after_farm + 2 * i + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - All Warriors should attack (group "attack").
        # - All Farmers should go back to the Village (group "village").
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```