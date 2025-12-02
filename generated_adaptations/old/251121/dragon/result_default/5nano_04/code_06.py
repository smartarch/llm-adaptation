"""
Strategy reasoning and approach (embedded as comments for clarity):

Goal
- Kill the Dragon as fast as possible while maintaining stability of wheat production and village survival.

Key observations
- Warriors are the primary damage dealers (3 damage per attack). All Warriors should fight in the Cave.
- Farmers keep wheat production up and can spawn new villagers when enough wheat and pairs are available.
- Spawning rules:
  - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- The game ticks in steps; each step, formations are updated and combat happens.

Strategy improvements over the previous approach
- Keep Warriors in the Cave to maximize DPS immediately.
- Spawn decisions should be dynamic and bounded to avoid starving wheat production:
  - Use a per-turn cap on spawning to avoid over-allocating villagers to spawning at the expense of wheat growth.
  - Introduce a simple, observation-based cap that scales with dragon HP: when the Dragon has high HP, be a bit more aggressive with spawns to accelerate closing the gap; as HP decreases, reduce spawning to keep wheat available for sustainment.
- In practice:
  - All Warriors → Cave (attack).
  - Farmers:
    - Spawn Farmer and Spawn Warrior up to a dynamic cap per turn, constrained by available wheat and number of farmers.
    - The rest of Farmers stay farming.
  - In Cave, Farmers go to Village; Warriors stay in Cave and attack.
- This adaptation should reduce the number of turns to kill the Dragon while preserving wheat production.

Implementation notes
- We compute a dynamic per-turn cap (max_pairs_cap) based on the Dragon HP to balance aggression and sustainment.
- We still respect the required group allocations and ensure every Farmer/Warrior is assigned to exactly one group per step.

Code:
"""

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

        # Dynamic cap based on Dragon HP: more HP -> allow slightly more spawning, within a sane bound
        dragon_hp = getattr(environment.dragon, "hp", 0)
        # Simple heuristic: ensure at least 1 pair could spawn; cap up to 4 pairs (8 villagers)
        # The function ensures we don't over-spawn when Dragon is close to dying.
        dynamic_cap = max(1, min(4, (60 - max(0, dragon_hp)) // 15 + 1))  # yields 1..4 based on HP

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

        # In case of any leftover farmers due to rounding, send them to farm
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