```py
# Improved adaptation strategy (implemented as a single Python class)
# Rationale:
# - All Warriors are kept in the Cave to attack the Dragon as soon as possible (per game rules).
# - Farmers stay in the Village to farm, providing a wheat income to drive spawning of more villagers.
# - Spawns are used to grow the village. To manage risk from Dragon's back-attacks in the Cave,
#   we adopt a cautious ramp-up: spawn farmers early to boost wheat, and delay spawning new Warriors
#   until later steps (step >= 5). This reduces the chance that a large Warrior cohort in the Cave
#   amplifies casualties from the Dragon's back-attacks while still enabling long-term DPS growth.
# - Spawning requirements:
#     - Farmer spawn: 2 villagers assigned to "spawn farmer" and 10 wheat.
#     - Warrior spawn: 2 villagers assigned to "spawn warrior" and 12 wheat.
# - We always move all Warriors to the Cave (group "cave") in assign_in_village, then allocate
#   the Farmers to "spawn farmer", "spawn warrior", or "farm" depending on wheat and the current step.
# - In assign_in_cave, Warriors attack (group "attack"); Farmers return to the Village (group "village").

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available at the farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Move all Warriors to the cave (they will attack the Dragon)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Determine how many Farmer spawns we can trigger this turn
        sF = min(len(farmers) // 2, wheat // 10)  # number of Farmer spawns this step
        spawn_farmers = farmers[:2 * sF]
        remaining_farmers = farmers[2 * sF:]

        # Determine whether to spawn Warriors this turn.
        # Strategy: delay Warrior spawns early (step < 5) to protect from dragon damage
        # and maximize wheat accumulation via Farming. After step 5, allow Warrior spawns
        # if wheat is available and there are enough Farmers left.
        sW = 0
        if step >= 5:
            # Use remaining farmers to spawn Warriors if possible
            sW = min(len(remaining_farmers) // 2, (wheat - 10 * sF) // 12)

        spawn_warriors = remaining_farmers[:2 * sW]
        remaining_farmers_after = remaining_farmers[2 * sW:]

        # Assign groups accordingly
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        # Farmers who are not spawning this turn will continue farming
        for c in remaining_farmers_after:
            environment.assign_group(c, "farm")

        # If there are any villagers left unassigned (shouldn't happen), put them in farm by default
        # but the logic above covers all current farmers.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack the Dragon with Warriors; Farmers go back to the Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```