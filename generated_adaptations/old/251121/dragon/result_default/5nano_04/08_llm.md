Reasoning and updated strategy:
- Objective remains to kill the Dragon as fast as possible while preserving wheat production.
- Observations:
  - Warriors are the primary damage dealers; they must go to the Cave and attack the Dragon.
  - Farmers sustain wheat production and can spawn new villagers if there is enough wheat.
  - Spawning requires pairs of villagers assigned to a spawn group plus a wheat cost (10 for farmers, 12 for warriors). The resulting new villagers can help ramp DPS in future turns.
- What to improve:
  - Increase spawning aggressiveness when resources allow, but do so with a higher, bounded cap so we don’t starve wheat growth early.
  - Tie the per-turn spawning cap to Dragon HP and current wheat, but allow more aggressive spawns when the Dragon is still strong to accelerate kill, and gracefully reduce spawning as HP falls to ensure finish within fewer turns.
- Plan:
  - In assign_in_village:
    - Move all Warriors to the cave (attack).
    - For Farmers, compute a dynamic cap on total pairs that can spawn this turn. The cap scales with Dragon HP (more HP → higher cap, up to a reasonable max) and is also limited by available wheat and number of farmers.
    - Spawn Farmers first (spawn farmer group), then Spawn Warriors (spawn warrior group) from the remaining farmers, and put the rest to Farm.
  - In assign_in_cave:
    - Keep Warriors in Attack; Farmers go to Village to continue farming/spawning.
- Expected outcome: More aggressive yet bounded spawning should reduce the number of turns to kill the Dragon while maintaining enough wheat for sustained growth, potentially lowering the average turns further than 15.7.

Code (Python) implementing the updated approach:

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

        Strategy (dynamic spawning, aggressive but bounded):
        - Move all Warriors to the cave (they will attack Dragon).
        - For Farmers, compute a per-turn cap on spawning that considers current Wheat and Dragon HP.
        - Spawn Farmers first up to the cap using 10 wheat per two Farmers.
        - Then spawn Warriors from remaining Farmers up to the cap if wheat allows (12 wheat per two Farmers).
        - The rest of Farmers stay Farming.
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

        # Dynamic cap: scale with Dragon HP, but cap to a reasonable max (to avoid over-spawning too early)
        # This heuristic yields more spawning when HP is lower, up to a practical limit.
        dynamic_cap = max(1, min(8, int((60 - max(0, dragon_hp)) / 7) + 1))  # yields 1..8

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