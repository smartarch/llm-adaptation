# Strategy rationale (embedded as comments for traceability):
# - Diagnosis of previous failures:
#   - Not enough early Warrior offense; spawn logic was rarely used (0 spawned Warriors).
#   - Wheat production was not leveraged effectively to create a pipeline of Warriors.
# - Improved plan:
#   - In assign_in_village:
#       - Move all Warriors to the Cave immediately so they can reach the Dragon and attack.
#       - Treat all Farmers as potential wheat producers this turn (assume 5 wheat per Farm turn).
#       - Greedily spawn as many Warriors as possible this turn, since Warriors are the primary damage dealers.
#         For k Warriors spawned this turn, require 2k Farmers and 12k wheat.
#       - With remaining Farmers, spawn as many additional Farmers as possible (2 Farmers + 10 wheat per spawn).
#         For f warps spawned this turn, require 2f Farmers and 10f wheat.
#       - Any Farmers not used for spawning stay in the Village to farm (increase future wheat production).
#   - In assign_in_cave:
#       - All Warriors attack (group "attack").
#       - All Farmers go back to Village (group "village").
# - This greedy, turn-by-turn approach aims to rapidly grow the Warrior force and sustain wheat production for ongoing spawns, increasing DPS toward killing the Dragon within the 30-step limit.
# - The implementation uses the environment.farm.wheat and an optimistic wheat production model (5 wheat per farming Farmer) to plan spawns this turn.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave (they should head to attack)
        for c in warriors:
            environment.assign_group(c, "cave")

        # If there are no farmers, nothing to spawn or farm; return
        F = len(farmers)
        if F == 0:
            return

        # 2) Compute Wheat assuming all Farmers farm this turn
        current_wheat = getattr(environment.farm, "wheat", 0)
        # Wheat produced if all farmers farm this turn
        wheat_if_all_farm = current_wheat + F * 5

        # 3) Decide how many Warriors to spawn this turn
        #   - Need 2 farmers and 12 wheat per Warrior spawn
        max_warriors_to_spawn = min(F // 2, wheat_if_all_farm // 12)

        # 4) Remaining farmers after allocating to Warrior spawns
        remaining_after_warriors = F - 2 * max_warriors_to_spawn

        # 5) Decide how many additional Farmers to spawn this turn with the remaining farmers
        #   - Need 2 farmers and 10 wheat per Farmer spawn
        max_farmers_to_spawn = min(remaining_after_warriors // 2,
                                   (wheat_if_all_farm - 12 * max_warriors_to_spawn) // 10)

        # 6) Final plan
        #   - Warriors spawned: 2 * max_warriors_to_spawn
        #   - Farmers spawned: 2 * max_farmers_to_spawn
        #   - Remaining farmers go to farming this turn
        spawned_warriors_count = 2 * max_warriors_to_spawn
        spawned_farmers_count = 2 * max_farmers_to_spawn
        farming_count = F - spawned_warriors_count - spawned_farmers_count  # could be 0 or more

        # 7) Assign groups based on the plan
        spawn_warrior_villagers = farmers[:spawned_warriors_count]
        spawn_farmer_villagers = farmers[spawned_warriors_count: spawned_warriors_count + spawned_farmers_count]
        farming_villagers = farmers[spawned_warriors_count + spawned_farmers_count:]

        for c in spawn_warrior_villagers:
            environment.assign_group(c, "spawn warrior")

        for c in spawn_farmer_villagers:
            environment.assign_group(c, "spawn farmer")

        for c in farming_villagers:
            environment.assign_group(c, "farm")

        # Note: Warriors were moved to cave earlier; Farmers not listed above default to farming.
        # If any edge-case farmers remain (shouldn't happen), ensure they farm:
        # (This is a safety net; in practice not needed due to slicing above.)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: All Warriors attack; Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")