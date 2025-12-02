# Strategy reasoning (embedded as comments for clarity)
# Objective: Improve the adaptation to kill the Dragon faster while keeping wheat production sustainable.
# Core ideas:
# - Warriors provide higher DPS (3) but suffer more from dragon retaliation if kept in the Cave.
# - Farmers are the wheat engine (5 wheat per farming action); keeping enough Farmers in Village is essential to spawn new villagers.
# - Spawn mechanics: For every two villagers assigned to a spawn group and enough wheat, a new villager is spawned.
#   - Spawn Farmer costs 10 wheat; Spawn Warrior costs 12 wheat.
# - Policy for this version:
#   - Always keep all Warriors in the Cave (policy requirement).
#   - In the Village, spawn Farmers as soon as we have at least two Farmers and 10 wheat.
#   - After spawning Farmers, spawn Warriors if we still have at least two spare Farmers and enough wheat (≥12 for a pair).
#   - The rest of Farmers stay farming.
# - Rationale: building wheat early helps sustain longer-term growth; then we incrementally add Warriors to boost DPS.
# - We explicitly re-assign all components each step to satisfy the explicit reassignment requirement.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group name constants (must match exact strings)
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        # Warriors are kept in cave by default; classify for convenience
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors -> cave; Farmers -> farm
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Read current wheat (guard against missing farm)
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Step 2: Spawn Farmers if possible (2 farmers and 10 wheat)
        num_farmers = len(farmers)
        spawn_farmers_pairs = 0
        if num_farmers >= 2 and wheat >= 10:
            # We can spawn as many Farmer pairs as wheat and farmer pairs allow
            spawn_farmers_pairs = min(num_farmers // 2, wheat // 10)

        spawn_farmers_count = 2 * spawn_farmers_pairs
        if spawn_farmers_count > 0:
            for c in farmers[:spawn_farmers_count]:
                environment.assign_group(c, SPAWN_FARMER)

        # Step 3: Spawn Warriors after Farmer spawns, from remaining farmers
        remaining_farmers_after_farm = num_farmers - spawn_farmers_count
        remaining_wheat_after_farm = wheat - (spawn_farmers_pairs * 10)

        spawn_warriors_pairs = 0
        if remaining_farmers_after_farm >= 2 and remaining_wheat_after_farm >= 12:
            spawn_warriors_pairs = min(remaining_farmers_after_farm // 2,
                                       remaining_wheat_after_farm // 12)

        spawn_warriors_count = 2 * spawn_warriors_pairs
        if spawn_warriors_count > 0:
            for c in farmers[spawn_farmers_count:
                             spawn_farmers_count + spawn_warriors_count]:
                environment.assign_group(c, SPAWN_WARRIOR)

        # Step 4: The rest stay farming
        rest_start = spawn_farmers_count + spawn_warriors_count
        for c in farmers[rest_start:]:
            environment.assign_group(c, FARM)

        # Notes:
        # - Warriors are already directed to the "cave" group by default.
        # - Spawn groups will create new villagers in subsequent steps per game rules.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group name constants
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors should attack
                environment.assign_group(c, ATTACK)
            else:
                # Farmers in the cave go back to the village
                environment.assign_group(c, VILLAGE)

        # Note: If there are any Farmers in the Cave due to edge cases, they are moved to village.