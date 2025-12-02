# SmartAdaptation for the Dragon Hunt game
#
# Reasoning and strategy:
# - Objective: kill the Dragon as fast as possible while not losing (keep at least some farmers producing wheat).
# - Constraints and rules:
#   * Warriors are the main damage dealers (3 dmg) and should be deployed to the Cave to attack.
#   * Farmers produce wheat (5 wheat) and can also be used in spawn groups to create new villagers.
#   * Spawning consumes wheat: 12 for a warrior (needs two villagers assigned to "spawn warrior"), 10 for a farmer (needs two villagers assigned to "spawn farmer").
#   * Every component must be assigned explicitly each step.
# - High-level adaptation policy:
#   1. Always send Warriors to the Cave; when in the Cave they attack the Dragon.
#   2. Farmers should primarily stay in the Village to farm, but we will use farmer pairs to spawn new Warriors whenever wheat allows.
#      Spawning Warriors speeds up dragon kill because they deal more damage than Farmers when attacking.
#   3. Keep a small minimum number of Farmers farming to ensure continuous wheat production. This prevents starving spawning operations.
#      The strategy reserves at least one farmer to farm (if any farmers exist). The rest of farmers can be allocated to spawn in pairs
#      whenever enough wheat is available. After spawning warriors as much as wheat permits (in whole pairs), if there are still spare
#      farmer pairs and wheat enough for farmer spawns, spawn farmers (helps increase long-term wheat production).
#   4. Any leftover farmers not assigned to spawn groups remain in "farm".
#   5. If a Farmer is in the Cave (should be rare), immediately send them back to the Village.
#
# This approach favors producing Warriors as long as wheat allows, while keeping at least one Farmer farming to maintain wheat flow.
#
# Implementation notes:
# - The class implements the two required methods:
#     assign_in_village(components, environment, group_ids, step)
#     assign_in_cave(components, environment, group_ids, step)
# - For spawning we create pairs greedily: prioritize spawn warrior (12 wheat per pair) then spawn farmer (10 wheat per pair).
# - All assignments are done via environment.assign_group(component, group_id).
#
# The code below follows the required interface and naming.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: list of villager components currently in the Village
        environment.farm.wheat available
        Assign groups: "farm", "cave", "spawn farmer", "spawn warrior"
        """
        # Collect farmers and warriors separately
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Ensure all Warriors in Village go to Cave (they should attack once there)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Prepare farmer assignment
        wheat = getattr(environment.farm, "wheat", 0)
        unassigned = list(farmers)

        # Reserve at least one farmer to farm if possible to maintain wheat income
        reserved_farmers = []
        if unassigned:
            # keep one farmer farming
            reserved_farmers.append(unassigned.pop(0))

        # Greedily spawn Warriors in pairs while wheat allows and at least 2 unassigned farmers remain
        while len(unassigned) >= 2 and wheat >= 12:
            # take two farmers and assign to spawn warrior
            f1 = unassigned.pop(0)
            f2 = unassigned.pop(0)
            environment.assign_group(f1, "spawn warrior")
            environment.assign_group(f2, "spawn warrior")
            wheat -= 12  # account for one warrior spawn per pair
            # continue to next possible pair

        # If still pairs available and wheat allows, optionally spawn Farmers (to increase long-term wheat)
        while len(unassigned) >= 2 and wheat >= 10:
            f1 = unassigned.pop(0)
            f2 = unassigned.pop(0)
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            wheat -= 10

        # Any remaining unassigned farmers go to farm
        for f in unassigned:
            environment.assign_group(f, "farm")

        # Assign reserved farmers to farm
        for f in reserved_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: list of villager components currently in the Cave
        Assign groups: "attack", "cave", "village"
        - All Warriors should attack
        - Farmers in the Cave should be sent back to Village
        """
        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                # Warriors should attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers should return to the Village to farm/spawn
                environment.assign_group(c, "village")