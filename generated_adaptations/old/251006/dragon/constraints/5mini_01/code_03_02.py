# SmartAdaptation for the Dragon Hunt game
#
# Reasoning and strategy:
# - Requirements:
#   * All Warriors should go to the Cave and attack the Dragon.
#   * All Farmers should remain in the Village and either farm or be used to spawn new villagers.
# - Goals:
#   * Kill the Dragon quickly (produce enough Warriors who attack).
#   * Keep enough Farmers farming to produce wheat for continuous spawning.
#   * Ensure both Farmers and Warriors get spawned over time.
# - Approach:
#   1. In the Village:
#       - Send every Warrior to "cave" (they will attack when in the Cave).
#       - For Farmers: reserve one farmer to always "farm" if any exist (so wheat production never fully stops).
#       - Use the remaining farmers in pairs to spawn Warriors first (12 wheat per pair) as many as possible,
#         then use remaining pairs to spawn Farmers (10 wheat per pair) as many as possible.
#       - Any farmers not used for spawning stay "farm".
#       - Track assignments by object id to avoid issues with unhashable component objects.
#   2. In the Cave:
#       - Farmers found in the Cave are immediately sent back to the Village ("village").
#       - All Warriors in the Cave should "attack" the Dragon (per requirement).
#
# Notes:
# - This version keeps the logic straightforward and deterministic, ensures every component is assigned
#   exactly once per call, and uses only valid group names for each location.
# - The spawning prioritizes Warriors to increase DPS, then spawns Farmers to sustain wheat production.
#
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Keep at least one farmer farming each turn if possible to keep wheat flowing.
        self.min_farmers_farming = 1

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Village
        Valid group ids: "farm", "cave", "spawn farmer", "spawn warrior"
        """
        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        wheat = getattr(environment.farm, "wheat", 0)

        # 1) Send all Warriors to Cave (they should attack from there)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Handle Farmers: reserve some to farm, use remaining in pairs to spawn.
        assigned_ids = set()

        reserve_count = min(self.min_farmers_farming, len(farmers))
        reserved = farmers[:reserve_count]
        remaining = farmers[reserve_count:]

        # Helper to find next two unassigned farmers in 'remaining' starting from index i
        # We'll just iterate sequentially.
        idx = 0

        # Spawn as many Warriors as possible from remaining farmers (2 farmers + 12 wheat per warrior)
        max_warrior_pairs_by_farmers = len(remaining) // 2
        max_warrior_pairs_by_wheat = wheat // 12
        warrior_pairs = min(max_warrior_pairs_by_farmers, max_warrior_pairs_by_wheat)

        for _ in range(warrior_pairs):
            # pick next two unassigned
            # skip any already assigned (shouldn't be any at this stage)
            while idx < len(remaining) and id(remaining[idx]) in assigned_ids:
                idx += 1
            f1 = remaining[idx]
            idx += 1
            while idx < len(remaining) and id(remaining[idx]) in assigned_ids:
                idx += 1
            f2 = remaining[idx]
            idx += 1
            environment.assign_group(f1, "spawn warrior")
            environment.assign_group(f2, "spawn warrior")
            assigned_ids.add(id(f1))
            assigned_ids.add(id(f2))
            wheat -= 12

        # After warrior spawns, spawn farmers from leftover remaining farmers (2 farmers + 10 wheat)
        leftover = [f for f in remaining if id(f) not in assigned_ids]
        idx = 0
        max_farmer_pairs_by_farmers = len(leftover) // 2
        max_farmer_pairs_by_wheat = wheat // 10
        farmer_pairs = min(max_farmer_pairs_by_farmers, max_farmer_pairs_by_wheat)

        for _ in range(farmer_pairs):
            f1 = leftover[idx]; f2 = leftover[idx + 1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            assigned_ids.add(id(f1))
            assigned_ids.add(id(f2))
            idx += 2
            wheat -= 10

        # Any farmers not used for spawning (including reserved) should farm
        for f in farmers:
            if id(f) not in assigned_ids:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Cave
        Valid group ids: "attack", "cave", "village"
        """
        # Send farmers in Cave back to Village; all Warriors attack (per requirement).
        for c in components:
            if getattr(c, "role", "") == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Warriors attack
                environment.assign_group(c, "attack")