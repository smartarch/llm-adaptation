```py
# Strategy reasoning (embedded as code comments)
# Goal: further reduce the number of turns to defeat the Dragon while keeping casualties manageable.
# Key ideas:
# - Keep Warriors in the Cave to maximize early DPS, but avoid overloading the Cave with non-farmers too early.
# - Grow the wheat base by farming Farmers, enabling more spawn opportunities for both Farmers and Warriors as needed.
# - Spawn Farmers aggressively when wheat allows, but also begin spawning Warriors earlier than before
#   to accelerate DPS growth, while keeping some Farmers in reserve to sustain wheat production.
# - Dynamic spawning policy:
#     - Farmer spawns: up to min(len(farmers)//2, wheat//10), with a cap that grows modestly with step.
#     - Warrior spawns: from the remaining Farmers, up to a cap that increases as wheat permits and as step grows.
# - In the Cave: always send Warriors to attack; Farmers return to Village to continue farming/spawning next steps.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move all Warriors to the Cave for immediate DPS
        for c in warriors:
            environment.assign_group(c, "cave")

        # Wheat available at the farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Maximum possible Farmer spawns this step (2 farmers per spawn, 10 wheat per spawn)
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Dynamic cap for Farmer spawns to balance risk and growth
        if step <= 2:
            sF = min(max_farm_spawns, 2)
        elif step <= 5:
            sF = min(max_farm_spawns, 4)
        else:
            sF = max_farm_spawns  # allow full use as the game progresses

        spawn_farmers = farmers[:2 * sF]
        remaining_farmers = farmers[2 * sF:]

        # Wheat remaining after Farmer spawns
        wheat_rem_after_farm = wheat - 10 * sF

        # Warrior spawns from remaining farmers
        # Spawn Warriors only if we have enough wheat; cap grows with step
        sW = 0
        if len(remaining_farmers) >= 2 and wheat_rem_after_farm >= 12:
            if step <= 2:
                sW = min(len(remaining_farmers) // 2, 2, wheat_rem_after_farm // 12)
            elif step <= 6:
                sW = min(len(remaining_farmers) // 2, 4, wheat_rem_after_farm // 12)
            else:
                sW = min(len(remaining_farmers) // 2, 6, wheat_rem_after_farm // 12)

        spawn_warriors = remaining_farmers[:2 * sW]
        remaining_farmers_after = remaining_farmers[2 * sW:]

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in remaining_farmers_after:
            environment.assign_group(c, "farm")

        # All Warriors are already in cave; farmers not spawning this turn will continue farming

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```