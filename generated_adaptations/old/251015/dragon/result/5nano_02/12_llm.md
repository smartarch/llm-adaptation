```py
# New improved adaptation strategy (aiming to win in fewer turns)
# Rationale:
# - All Warriors should go to the Cave to contribute to Dragon DPS as early as possible.
# - Farmers stay in the Village to farm and grow wheat, enabling spawning of more villagers.
# - Spawn Farmers aggressively but with a cap to avoid risking too many villagers in the Cave early on.
# - Spawn Warriors later (once we have some wheat and enough farmers to spare) to boost DPS without starving farming.
# - This balance aims to reduce the total number of turns to kill the Dragon while keeping casualties manageable.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role present in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move all Warriors to the Cave so they can start attacking the Dragon
        for c in warriors:
            environment.assign_group(c, "cave")

        # Wheat available in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawn Farmers aggressively but cap to avoid excessive cave exposure
        sFmax = min(len(farmers) // 2, wheat // 10)  # max possible Farmer spawns this turn
        sF = min(sFmax, 4)  # cap to 4 spawns per step

        spawn_farmers = farmers[:2 * sF]
        remaining_farmers = farmers[2 * sF:]

        # Determine potential Warrior spawns from remaining farmers
        # Spawn Warriors only after step >= 1 to reduce early risk
        sW = 0
        remaining_wheat = wheat - 10 * sF
        if step >= 1:
            sW = min(len(remaining_farmers) // 2, max(0, remaining_wheat // 12), 3)  # cap at 3

        spawn_warriors = remaining_farmers[:2 * sW]
        remaining_farmers_after = remaining_farmers[2 * sW:]

        # Assign groups accordingly
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in remaining_farmers_after:
            environment.assign_group(c, "farm")

        # Note: All non-spawning farmers remain farming; all Warriors are in the cave already.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack the Dragon; Farmers return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```