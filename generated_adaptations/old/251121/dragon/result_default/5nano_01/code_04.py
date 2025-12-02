# Strategy justification and approach (embedded as comments for clarity):
# 
# Objective: Kill the Dragon as fast as possible while staying alive for up to 30 steps.
# Observations:
# - Warriors deal 3 damage when attacking; Farmers deal 1 damage.
# - All Warriors should end up in the Cave and then Attack the Dragon.
# - Farmers should stay in the Village to farm (produce wheat) and to spawn new villagers when resources allow.
# - Spawning rules:
#     - Spawn Farmer: requires 2 Farmers in the "spawn farmer" group and 10 wheat in the Farm.
#     - Spawn Warrior: requires 2 Farmers in the "spawn warrior" group and 12 wheat in the Farm.
# - Wheat production: Farmers in the Farm produce 5 wheat each farming action.
# - Dragon retaliation is risky: it can damage all villagers in Cave or eat one random villager in Cave.
# - To improve reliability and speed, we should:
#   1) Keep all Warriors in the Cave and pushing damage as early as possible.
#   2) Keep enough Farmers in the Village to generate wheat to enable spawning.
#   3) Prefer spawning both Farmers and Warriors only when we have a healthy wheat reserve to avoid starving farming momentum.
#   4) Spawn Warrior first (when possible) to accelerate early damage, then spawn Farmers to grow wheat reserves, while always maintaining some Farmers for farming.
#   5) In the Cave phase, send all non-Warrior villagers back to the Village, so only Warriors stay to Attack.
#
# Adaptation plan implemented in code:
# - assign_in_village:
#     - Move all Warriors to the cave (group "cave"), so they will eventually Attack in assign_in_cave.
#     - For Farmers:
#       - Compute how many Warrior spawns we can fund this turn: min(farmers//2, wheat//12).
#       - Allocate 2* Warrior-spawn farmers to "spawn warrior".
#       - With remaining wheat, compute how many Farmer spawns we can fund: min(remaining_farmers//2, remaining_wheat//10).
#       - Allocate 2* Farmer-spawn farmers to "spawn farmer".
#       - The rest of Farmers go to "farm".
# - assign_in_cave:
#     - All Warriors go to "attack".
#     - All Farmers go to "village" (return to Village to farm/spawn).
#
# This strategy aims to aggressively increase early DPS (via Warriors) while maintaining steady wheat production for spawning and growth.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to the Cave (to join the attacking Warriors)
        - "spawn farmer": form pairs to spawn new Farmers (needs 10 wheat per spawn)
        - "spawn warrior": form pairs to spawn new Warriors (needs 12 wheat per spawn)
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (to eventually Attack)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Now handle Farmers: allocate spawning first, then farming
        total_wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            total_wheat = getattr(farm_obj, "wheat", 0)

        # Determine how many Warrior spawns we can fund this turn
        # Each Warrior spawn consumes 2 farmers + 12 wheat
        max_warrior_spawns = min(len(farmers) // 2, total_wheat // 12)

        idx = 0
        # Assign 2*max_warrior_spawns farmers to "spawn warrior"
        for _ in range(max_warrior_spawns * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Update wheat after Warrior spawns
        wheat_after_warriors = total_wheat - max_warrior_spawns * 12

        # Remaining farmers that can participate in Farmer spawns
        remaining_farmers_for_spawns = len(farmers) - max_warrior_spawns * 2

        # Determine how many Farmer spawns we can fund this turn with remaining wheat
        max_farmer_spawns = min(remaining_farmers_for_spawns // 2, wheat_after_warriors // 10)

        for _ in range(max_farmer_spawns * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers go to farming
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - "attack": Attack the Dragon (Warriors)
        - "cave": Stay in the Cave
        - "village": Go to the Village (Farmers return to farming)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should return to the Village to farm/spawn
                environment.assign_group(c, "village")