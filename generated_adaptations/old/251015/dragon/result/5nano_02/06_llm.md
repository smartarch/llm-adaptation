```py
# Strategy reasoning (embedded as comments in the code)
# Goal: Improve win rate by prioritizing rapid growth of the village (Farmers) to increase long-term wheat supply,
# while ensuring Warriors reliably reach the Dragon quickly.
# Policy:
# - All Warriors are sent to the Cave to be able to attack the Dragon as soon as possible.
# - Farmers stay in the Village to farm. We prioritize spawning new Farmers whenever we have enough wheat,
#   because more Farmers mean more wheat production and more potential future spawners.
# - We will not spawn Warriors this turn to keep wheat dedicated to farming early on, preventing
#   wheat starvation that could delay farming velocity. This is a conservative approach to grow the village first,
#   then ramp up Warrior numbers once wheat stock is sufficient.
# - The spawning mechanic requires 2 villagers assigned to the spawn group and a fixed amount of wheat.
#   We allocate 2*s farmers to the "spawn farmer" group, limited by floor(len(farmers)/2) and wheat//10.
# - Remaining farmers are assigned to "farm" in order to continuously accumulate wheat for future spawns.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available in the farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # All Warriors should eventually go to the Cave to attack; move them there now
        for c in warriors:
            environment.assign_group(c, "cave")

        # Spawn Farmers as much as possible this turn (2 farmers required per spawn, 10 wheat per spawn)
        s1 = min(len(farmers) // 2, wheat // 10)  # number of Farmer spawns this step
        spawn_farmers = farmers[:2 * s1]
        remaining_farmers = farmers[2 * s1:]

        # Assign 2*s1 farmers to "spawn farmer" to trigger spawns
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        # Remaining farmers are assigned to farming (to keep wheat production growing)
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # Note: We intentionally do not assign any farmers to "spawn warrior" to keep wheat reserved for farming early.
        # If later turns have surplus wheat, the existing spawn Warrior option can be revisited.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, let Warriors attack the Dragon; Farmers should return to the Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```