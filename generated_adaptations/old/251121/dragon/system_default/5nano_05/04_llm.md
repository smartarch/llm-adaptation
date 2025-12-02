```py
"""
Reasoning and adaptation strategy (embedded for traceability):
- The game rewards both damage output and population growth via wheat. Killing the Dragon quickly benefits from more Warriors in the Cave, but Wheat is needed to spawn new villagers.
- To accelerate wins, use a two-stage plan:
  1) InVillage: Move all Warriors to the Cave to maximize DPS early. Use Farmers to spawn more villagers whenever Wheat allows:
     - Spawn Farmer: allocate as many pairs of villagers as possible to "spawn farmer" provided there is at least 10 Wheat per pair (one spawned Farmer per pair of villagers).
     - Spawn Warrior: with any remaining Wheat, allocate additional pairs of villagers to "spawn warrior" (requires 12 Wheat per pair).
     - The rest of Farmers stay farming in the Village to accumulate Wheat for future spawns.
  2) InCave: Keep Warriors in the Cave attacking the Dragon ("attack"). Farmers stay in the Village ("village") to continue farming and enabling future spawns.
- This strategy dynamically uses Wheat to grow the number of villagers, particularly Warriors, to increase DPS in the Cave, while maintaining Wheat production to sustain spawning over time.
- All components must be assigned to exactly one group each step. The spawning logic uses the platform’s cost rules (2 villagers required per spawn, with the Wheat cost per spawn).

Code implementing the strategy:

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Strategy in Village:
        - Warriors -> "cave" (will attack Dragon when in Cave)
        - Farmers -> either:
            * "spawn farmer" groups (2 villagers per spawn, 10 wheat per spawn)
            * "spawn warrior" groups (2 villagers per spawn, 12 wheat per spawn)
            * remaining -> "farm" (stay in Village and farm)
        This aims to balance population growth with Wheat production to enable rapid spawning.
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current Wheat in Farm
        W = getattr(getattr(environment, "farm", None), "wheat", 0)

        # How many spawn events we can attempt for farmers
        max_spawn_farmers = len(farmers) // 2
        p_farm = min(max_spawn_farmers, W // 10)

        # Wheat remaining after spawning farmers
        W_remaining = W - p_farm * 10

        # Remaining farmers available for spawning warriors
        remaining_farmers_after_farm_spawns = len(farmers) - (2 * p_farm)
        p_war = min(remaining_farmers_after_farm_spawns // 2, W_remaining // 12)

        # Define groups
        spawn_farmers = farmers[:2 * p_farm]
        spawn_warriors = farmers[2 * p_farm: 2 * p_farm + 2 * p_war]
        farmers_to_farm = farmers[2 * p_farm + 2 * p_war :]

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in farmers_to_farm:
            environment.assign_group(c, "farm")

        # Warriors go to Cave to attack
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Strategy in Cave:
        - All Warriors -> "attack" (attack the Dragon)
        - All Farmers -> "village" (return to Village to farm/spawn)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```