Reasoning and improved strategy

Goal-aware refinement:
- Maintain the core rules: all Warriors go to the Cave and attack; all Farmers stay in the Village to farm and enable spawning.
- Improve win speed by balancing early DPS with wheat production. Early on, we want more Warriors in the Cave to damage the Dragon quickly. As wheat accumulates, we shift to spawning Farmers to boost long-term wheat production and population, then spawn more Warriors if wheat allows.
- Step-aware spawning: use a simple heuristic that prioritizes spawning Warriors in the first few steps (to boost immediate DPS) and then prioritizes spawning Farmers in later steps (to sustain wheat production and additional population). This increases the chance to kill the Dragon sooner while reducing risk of running out of villagers due to dragon counterattacks.

Implementation outline:
- In assign_in_village:
  - Move all Warriors to the Cave (they will attack in the Cave).
  - Let step guide spawning:
    - If step <= 8: prefer spawning Warriors first (using 2 farmers per Warrior and 12 wheat per Warrior), then spawn Farmers with any remaining wheat.
    - If step > 8: prefer spawning Farmers first (using 2 farmers per Farmer and 10 wheat per Farmer), then spawn Warriors with any remaining wheat.
  - Any remaining Farmers stay in the Village and farm.
- In assign_in_cave:
  - All Warriors stay in the attack group.
  - Farmers return to the Village.

This approach aims for earlier Dragon damage while still growing wheat/population to sustain DPS growth, increasing the chance to kill the Dragon within fewer turns.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village to farm wheat
        - cave: go to the Cave (for Warriors)
        - spawn farmer: for every two villagers in this group and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers in this group and 12 wheat, spawn a Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors should move to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village, but we may use some to spawn
        wheat = int(getattr(environment.farm, "wheat", 0))

        if step <= 8:
            # Early steps: spawn Warriors first to boost DPS
            max_war_spawns = min(len(farmers) // 2, wheat // 12) if len(farmers) >= 2 else 0
            kw = max_war_spawns
            remaining_farmers_after_war = len(farmers) - 2 * kw
            remaining_wheat_after_war = wheat - 12 * kw

            max_farm_spawns = min(remaining_farmers_after_war // 2, remaining_wheat_after_war // 10) if remaining_farmers_after_war >= 2 else 0
            kf = max_farm_spawns
        else:
            # Later steps: spawn Farmers first to boost wheat/population
            max_farm_spawns = min(len(farmers) // 2, wheat // 10) if len(farmers) >= 2 else 0
            kf = max_farm_spawns
            remaining_wheat_after_farm = wheat - 10 * kf
            remaining_farmers_after_farm = len(farmers) - 2 * kf
            max_war_spawns = min(remaining_farmers_after_farm // 2, remaining_wheat_after_farm // 12) if remaining_farmers_after_farm >= 2 else 0
            kw = max_war_spawns

        # Allocate farmers to groups
        idx = 0

        # Assign 2*kw farmers to "spawn warrior"
        for _ in range(2 * kw):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Assign 2*kf farmers to "spawn farmer"
        for _ in range(2 * kf):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers go to "farm" (stay in Village and farm)
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors should attack the Dragon
        - cave: stay in the Cave (if any non-Warrior ends up here, keep them here)
        - village: Go to the Village
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should return to Village
                environment.assign_group(c, "village")
```