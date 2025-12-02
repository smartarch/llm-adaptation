Reasoning:
- Objective remains to kill the Dragon quickly while keeping wheat production stable.
- Key tuning: aggressive but bounded spawning to accelerate DPS without starving wheat.
- Approach:
  - Always keep Warriors in the Cave to maximize DPS (attack group).
  - In the Village, compute a per-turn spawning cap that scales with Dragon HP (more HP allows a bit more spawning early; as HP drops, cap reduces). This balances short-term damage with long-term sustainability.
  - Spawn Farmers first (needs 10 wheat per 2 Farmers), then spawn Warriors from the remaining Farmers (needs 12 wheat per 2 Farmers). The rest of Farmers stay farming.
  - In the Cave, keep Warriors in the Attack group; Farmers return to Village to continue farming/spawning.
- This approach aims to reduce the average turns to win by increasing early DPS while maintaining resource flow for future turns.

Code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave (for Warriors)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned

        Strategy (bounded aggressive spawning):
        - Move all Warriors to the cave (they will attack Dragon).
        - Compute a per-turn cap on total spawning pairs based on Dragon HP (more HP -> allow more spawning, capped).
        - Spawn Farmers first up to cap (requires 10 wheat per 2 Farmers).
        - Then spawn Warriors from the remaining Farmers if wheat allows (requires 12 wheat per 2 Farmers).
        - The rest of Farmers stay in Farm.
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        total_farmers = len(farmers)

        # Move all warriors to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        if total_farmers == 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)
        dragon_hp = getattr(environment.dragon, "hp", 0)

        # Dynamic cap: scale with Dragon HP, capped to a reasonable maximum (to avoid over-spawning too early)
        # More HP -> higher cap, but cap at 6 pairs (12 villagers) for safety.
        dynamic_cap = max(1, min(6, int(dragon_hp / 8) + 1))  # yields 1..6

        # Spawn Farmer first
        spawn_farm_pairs = 0
        if wheat >= 10 and total_farmers >= 2:
            spawn_farm_pairs = min(total_farmers // 2, wheat // 10, dynamic_cap)
        spawn_farm_count = 2 * spawn_farm_pairs

        remaining_farmers_after_farm = total_farmers - spawn_farm_count
        wheat_after_farm = wheat - (spawn_farm_pairs * 10)

        # Then spawn Warriors from remaining farmers
        spawn_war_pairs = 0
        if wheat_after_farm >= 12 and remaining_farmers_after_farm >= 2:
            spawn_war_pairs = min(remaining_farmers_after_farm // 2, wheat_after_farm // 12, dynamic_cap)
        spawn_war_count = 2 * spawn_war_pairs

        farm_count = remaining_farmers_after_farm - spawn_war_count

        idx = 0
        # Assign to spawn farmer
        for _ in range(spawn_farm_count):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        # Assign to spawn warrior
        for _ in range(spawn_war_count):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        # Assign remaining to farm
        for _ in range(farm_count):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Any leftover farmers (edge cases) also go to farm
        while idx < total_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village

        Strategy:
        - All Warriors attack; Farmers go to Village to continue farming/spawning.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
```