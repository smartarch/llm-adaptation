```py
# Adaptation strategy reasoning (embedded as code comments)
# Goal: Kill the Dragon as fast as possible by coordinating villagers.
# Key rules we will follow:
# - All Warriors should go to the Cave, then attack the Dragon.
# - All Farmers should stay in the Village to farm or spawn new villagers.
# - Spawning: there are two spawn groups in the village:
#   - "spawn farmer": for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
#   - "spawn warrior": For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
# Strategy:
# - In assign_in_village:
#   - Keep all Warriors in the village assignment to go to the Cave (group "cave").
#   - For Farmers, attempt to spawn new Farmers as soon as wheat allows:
#     - Let s1 = min(number_of_farmers // 2, wheat // 10). This is the maximum number of Farmer spawns given current wheat.
#     - Assign 2*s1 Farmers to "spawn farmer" to trigger spawns, and
#       the remaining Farmers (if any) to either "spawn warrior" (if wheat allows) or "farm".
#     - Attempt to spawn Warriors using remaining wheat if possible by allocating 2 farmers to "spawn warrior" per 12 wheat.
# - In assign_in_cave:
#   - All villagers in the cave: Warriors attack (group "attack"), Farmers return to Village (group "village").
# - This approach ensures Warriors reach the Dragon quickly, Farmers stay to produce wheat and spawn more villagers, and we leverage spawning to grow the village.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # All warriors should move to the cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # Spawn Farmers: as many as possible given 2 per spawn and 10 wheat per spawn
        s1 = min(len(farmers) // 2, wheat // 10)  # number of Farmer spawns this step
        spawn_farmers = farmers[:2 * s1]
        remaining_farmers = farmers[2 * s1:]

        # Spawn Warriors: use remaining farmers if enough wheat remains
        s2 = min(len(remaining_farmers) // 2, (wheat - 10 * s1) // 12)
        spawn_warriors = remaining_farmers[:2 * s2]
        remaining_farmers_after = remaining_farmers[2 * s2:]

        # Assign groups according to possibility
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in remaining_farmers_after:
            environment.assign_group(c, "farm")

        # Any farmers not mentioned are already handled in remaining_farmers or spawned

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack the Dragon with Warriors; Farmers go back to the village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```