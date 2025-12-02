import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Current wheat available in the farm
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Maximum spawns of Farmers we can do: each requires 2 farmers and 10 wheat
        possible_spawns = min(len(farmers) // 2, int(wheat // 10))

        # Assign 2*possible_spawns farmers to spawn_farmers group
        spawn_farmers = farmers[:2 * possible_spawns]
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        # Remaining farmers go to farming in village
        remaining_farmers = farmers[2 * possible_spawns:]
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

        # All Warriors should go to the Cave to attack
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # All Warriors should attack the Dragon; Farmers should go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")