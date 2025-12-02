# Adaptation strategy reasoning (embedded as code comments)
# Goal: Kill the Dragon as fast as possible by coordinating villagers.
# Key rules we will follow:
# - All Warriors should go to the Cave, then attack the Dragon.
# - All Farmers should stay in the Village to farm or spawn new villagers.
# - Spawning: there are two spawn groups in the village:
#   - "spawn farmer": for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
#   - "spawn warrior": for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
# Strategy:
# - In assign_in_village:
#   - Keep all Warriors in the village assignment to go to the Cave (group "cave").
#   - For Farmers, attempt to spawn new Farmers as soon as wheat allows:
#     - Let s = min(number_of_farmers // 2, wheat // 10). This is the maximum number of spawns for Farmers given current wheat.
#     - Assign 2*s Farmers to "spawn farmer" to trigger spawns, and the remaining Farmers (if any) to "farm".
#   - This keeps farming ongoing to accumulate wheat and periodically expands the village with new Farmers.
# - In assign_in_cave:
#   - All villagers currently in the Cave (likely Warriors) will be assigned to "attack" to hit the Dragon.
#   - If any Farmers accidentally end up in the Cave, assign them back to "village" to continue farming.
# - This approach ensures Warriors reliably reach the Dragon quickly, Farmers stay in Village to sustain wheat production and spawning, and we leverage the spawning mechanic to grow the number of villagers over time.

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

        # Max number of farmer spawns we can trigger this step
        s = min(len(farmers) // 2, wheat // 10)

        # Choose 2*s farmers to assign to the spawn farmer group
        spawn_farmers = farmers[:2 * s]
        remaining_farmers = farmers[2 * s:]

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # All warriors should go to the cave (to eventually attack)
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack the Dragon with warriors; farmers go back to village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers return to the village
                environment.assign_group(c, "village")