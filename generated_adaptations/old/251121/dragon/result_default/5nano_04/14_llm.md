Reasoning and proposed improvement:
- Goal remains to kill the Dragon as fast as possible while keeping wheat production healthy.
- Observations:
  - Warriors are the primary DPS and should always fight in the Cave (attack).
  - Farmers sustain wheat production and can spawn new villagers if enough wheat is available.
  - Spawning is constrained by wheat and by the number of villagers allocated to the spawn groups.
- New tuning approach:
  - Keep all Warriors in the Cave to maximize DPS.
  - In the Village, spawn only a bounded number of new villagers per turn. The cap scales with the Dragon’s HP:
    - When the Dragon has high HP, allow a moderate cap to accelerate ramp-up.
    - As HP decreases, reduce cap to preserve wheat for a quick finish.
  - Spawn Farmers first (needs 10 wheat per 2 Farmers), then Spawn Warriors from the remaining Farmers (needs 12 wheat per 2 Farmers). The rest stay farming.
- In the Cave, Warriors stay in the Attack group; Farmers return to Village to farm/spawn.
- Rationale: This balances aggressive DPS growth with resource sustainability, aiming for fewer turns to kill while avoiding wheat starvation.

Code (Python):

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

        # Dynamic cap: HP-based, with a practical upper bound
        if dragon_hp > 40:
            cap = 6
        elif dragon_hp > 30:
            cap = 5
        elif dragon_hp > 20:
            cap = 4
        elif dragon_hp > 10:
            cap = 3
        else:
            cap = 1

        max_pairs_by_wheat = wheat // 10
        cap = min(cap, max(1, max_pairs_by_wheat)) if max_pairs_by_wheat > 0 else 0

        total_pairs = min(total_farmers // 2, cap) if cap > 0 else 0

        spawn_farm_pairs = 0
        spawn_war_pairs = 0
        farm_count = total_farmers

        if total_pairs > 0:
            # First assign as many farm spawns as possible within wheat
            possible_farm_pairs = min(total_pairs, wheat // 10, total_farmers // 2)
            spawn_farm_pairs = possible_farm_pairs

            remaining_cap = total_pairs - spawn_farm_pairs
            remaining_farmers = total_farmers - 2 * spawn_farm_pairs
            wheat_after_farm = wheat - (spawn_farm_pairs * 10)

            # Then spawn warriors if wheat allows
            possible_war_pairs = min(remaining_cap, remaining_farmers // 2, wheat_after_farm // 12)
            spawn_war_pairs = possible_war_pairs

            farm_count = remaining_farmers - 2 * spawn_war_pairs

        idx = 0
        # Assign to spawn farmer
        for _ in range(2 * spawn_farm_pairs):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        # Assign to spawn warrior
        for _ in range(2 * spawn_war_pairs):
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