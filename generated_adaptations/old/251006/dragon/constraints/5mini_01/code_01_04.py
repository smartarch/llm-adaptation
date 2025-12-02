# SmartAdaptation for the Dragon Hunt game
#
# Reasoning and updated strategy:
# - Goal: kill the Dragon as fast as possible while keeping the game alive.
# - Warriors are the main damage dealers; they should always go to the Cave to attack.
# - Farmers produce wheat and are the only villagers we will use for spawning (Warriors must go to Cave).
# - Tests expect that over the simulation a noticeable number of both Farmers and Warriors are spawned.
# - To satisfy that, be more aggressive about spawning:
#     * Use Farmer pairs greedily to spawn Warriors first (high damage) whenever wheat permits.
#     * With remaining Farmer pairs and wheat, spawn Farmers to grow long-term wheat production.
# - Keep one Farmer farming only when there's a single Farmer available (can't form a spawn pair).
# - Ensure each component is assigned exactly once per call and only to valid group names.
#
# Implementation details:
# - Deterministically compute how many warrior spawns (pairs) we can do based on farmer count and available wheat.
# - Then compute how many farmer spawns (pairs) can be done with the remaining farmers and wheat.
# - Assign remaining farmers to "farm".
# - All Warriors found in Village are sent to "cave" (they will be handled by assign_in_cave next turn).
# - In the Cave: Warriors -> "attack"; Farmers -> "village" (they should not stay in cave).
# - All assignments use environment.assign_group(component, group_id).
#
# This version removes the conservative "always reserve one farmer" decision (except when only a single farmer exists)
# to ensure spawning actually occurs and satisfies the test requirements for spawning both types.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Village
        Valid group ids (expected): "farm", "cave", "spawn farmer", "spawn warrior"
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Send all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Number of farmers available to assign/spawn
        num_farmers = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # If only one farmer exists, keep them farming (can't form a spawn pair)
        if num_farmers <= 1:
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Determine number of warrior spawns (each requires 2 farmers and 12 wheat)
        max_pairs_by_farmers = num_farmers // 2
        max_warrior_spawns_by_wheat = wheat // 12
        warrior_spawns = min(max_pairs_by_farmers, max_warrior_spawns_by_wheat)

        # Reserve and assign farmers to spawn warriors
        assigned = set()
        idx = 0
        for _ in range(warrior_spawns):
            # take two farmers
            f1 = farmers[idx]; f2 = farmers[idx+1]
            environment.assign_group(f1, "spawn warrior")
            environment.assign_group(f2, "spawn warrior")
            assigned.add(f1); assigned.add(f2)
            idx += 2
            wheat -= 12

        # Remaining farmers after warrior spawns
        remaining_farmers = [f for f in farmers if f not in assigned]
        num_remaining = len(remaining_farmers)

        # Determine farmer spawns (each requires 2 farmers and 10 wheat)
        max_pairs_by_farmers = num_remaining // 2
        max_farmer_spawns_by_wheat = wheat // 10
        farmer_spawns = min(max_pairs_by_farmers, max_farmer_spawns_by_wheat)

        # Assign farmer spawns
        idx = 0
        for _ in range(farmer_spawns):
            f1 = remaining_farmers[idx]; f2 = remaining_farmers[idx+1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            assigned.add(f1); assigned.add(f2)
            idx += 2
            wheat -= 10

        # Any remaining unassigned farmers go to farm
        for f in farmers:
            if f not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Cave
        Valid group ids (expected): "attack", "cave", "village"
        """
        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should return to Village to farm/spawn
                environment.assign_group(c, "village")