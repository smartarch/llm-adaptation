```py
# Strategy reasoning (embedded as comments for clarity)
# Objective: Improve the adaptation so the Dragon is killed faster while still sustaining wheat production
# and keeping villagers alive. Observations:
# - Warriors provide higher DPS (3) but suffer from dragon retaliation if in the Cave.
# - Farmers are the wheat engine: 5 wheat per farming action (Farmers start with HP 4).
# - Spawn mechanics: For every two villagers in a spawn group and enough wheat, one new villager is spawned.
#   - Spawn Farmer costs 10 wheat; Spawn Warrior costs 12 wheat.
# - To win, we want a balance: enough Warriors in the Cave to deal DPS, but also enough Farmers producing wheat
#   so we can continue spawning more villagers and possibly more Warriors over time.
# - Previous approach always prioritized spawning farmers first, then warriors, which can delay DPS growth when wheat is abundant.
# Improved approach:
# - In assign_in_village, keep all Warriors in the Cave (policy requirement).
# - Spawn Warriors first when possible (prioritize DPS acceleration), then spawn Farmers with any remaining wheat.
# - Use a deterministic approach that can scale: compute max possible Warrior spawns from current Farmers and Wheat,
#   then compute max possible Farmer spawns from the remaining Farmers and remaining Wheat.
# - Ensure explicit reassignment for every component each step to satisfy the explicit reassignment rule.

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
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors go to cave; Farmers stay in village farming by default
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Read current wheat
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Step 2: Compute how many warriors we can spawn this turn (prioritize DPS)
        num_farmers = len(farmers)
        max_warrior_spawns = min(num_farmers // 2, wheat // 12)
        spawn_warriors_count = 2 * max_warrior_spawns

        if spawn_warriors_count > 0:
            # Move the first 2*max_warrior_spawns farmers to the SPAWN_WARRIOR group
            for c in farmers[:spawn_warriors_count]:
                environment.assign_group(c, SPAWN_WARRIOR)

        # Step 3: Compute how many farmers we can spawn with remaining wheat after warrior spawns
        remaining_wheat_after_warriors = wheat - (max_warrior_spawns * 12)
        remaining_farmers = farmers[spawn_warriors_count:]

        max_farmer_spawns = min(len(remaining_farmers) // 2, remaining_wheat_after_warriors // 10)
        spawn_farmers_count = 2 * max_farmer_spawns

        if spawn_farmers_count > 0:
            for c in remaining_farmers[:spawn_farmers_count]:
                environment.assign_group(c, SPAWN_FARMER)

        # Step 4: Any farmers not in spawn groups stay farming
        rest_start = spawn_warriors_count + spawn_farmers_count
        for c in farmers[rest_start:]:
            environment.assign_group(c, FARM)

        # Note:
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
                # Farmers in the cave should go back to the village
                environment.assign_group(c, VILLAGE)

        # If there happens to be any Farmer in the Cave due to edge cases, they are moved to the village.
```