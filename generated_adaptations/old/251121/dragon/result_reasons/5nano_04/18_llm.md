Reasoning and updated strategy

Goal: improve win rate by delivering faster Dragon DPS while maintaining a reliable wheat-based growth pipeline, but without over-spawning or risking excessive losses in the cave.

Key ideas in this iteration:
- Dynamic, step-aware escalation: instead of a fixed cap each step, we adapt how aggressively we move Warriors to the Cave based on the current situation.
  - Gradually move Warriors to the Cave, with the cap increasing as steps progress.
  - If the Dragon is already weakened (low HP), push more Warriors to the Cave to capitalize on the window for a kill.
- Budgeted spawning with disjoint pairs:
  - Spawn Farmer pairs first (2 Farmers per spawn, 10 wheat per spawn), capped per step to prevent wheat waste and ensure growth across many steps.
  - After Farmer spawns, spawn Warrior pairs (2 Farmers per spawn, 12 wheat per spawn), also capped per step.
  - Ensure we never reuse the same villagers for multiple spawns in a single step.
- Farmers stay in the Village to keep producing wheat; Warriors eventually move to the Cave to attack.
- In the Cave, Warriors attack; Farmers return to the Village.

This approach aims to:
- Attack early but in a controlled manner, while growing both the Farmer and Warrior populations to sustain DPS.
- Adapt to the Dragon’s HP by increasing aggression if the Dragon is weakened.

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step-aware escalation with budgeted spawning and dynamic dragon awareness.
        if not components:
            return

        # Split villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Gradually move Warriors to the Cave
        if len(warriors) > 0:
            # Base cap grows with step (1,2,3,4,...)
            base_cap = min(len(warriors), max(1, step // 2 + 1))
            # If Dragon HP is low, push more Warriors to cave to try for a kill
            try:
                dragon_hp = environment.dragon.hp
            except Exception:
                dragon_hp = None
            if dragon_hp is not None and dragon_hp <= 15:
                base_cap = min(base_cap + 2, len(warriors))
            move_cap = min(base_cap, len(warriors))

            for i in range(move_cap):
                environment.assign_group(warriors[i], "cave")

        # 2) Keep Farmers in the Village (farm)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Aggressive, budgeted spawning (per step)
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmer spawns: 2 farmers per spawn, 10 wheat per spawn
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        max_farm_spawns = min(max_farm_spawns, 3)  # cap per-step spawns

        # Trigger farmer spawns using disjoint farmer pairs
        for i in range(max_farm_spawns):
            c1 = farmers[2 * i]
            c2 = farmers[2 * i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")

        # Update wheat budget after farmer spawns
        wheat_after_farm = wheat - max_farm_spawns * 10
        idx_after_farm = 2 * max_farm_spawns

        remaining_farmers_for_war = len(farmers) - idx_after_farm

        # Warrior spawns: 2 farmers per spawn, 12 wheat per spawn
        max_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)
        max_war_spawns = min(max_war_spawns, 3)  # cap per-step spawns

        # Trigger warrior spawns using disjoint farmer pairs after farmer-spawns
        for i in range(max_war_spawns):
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