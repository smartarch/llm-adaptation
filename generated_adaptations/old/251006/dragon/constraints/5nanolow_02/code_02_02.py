import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Distribute villagers in the village into:
        - farm: Farmers stay in Village to farm
        - cave: Warriors go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All existing Warriors should go to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village: decide on spawning or farming
        num_farmers = len(farmers)
        if num_farmers == 0:
            return  # nothing else to do

        # Wheat available for spawning
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        to_spawn_warriors = []
        remaining_farmers = farmers[:]

        # If we have at least 2 farmers and at least 12 wheat, spawn 1 new Warrior
        if len(remaining_farmers) >= 2 and wheat >= 12:
            to_spawn_warriors = remaining_farmers[:2]
            remaining_farmers = remaining_farmers[2:]
            # This would conceptually consume 12 wheat; we reflect that in the remaining wheat count
            wheat -= 12

        to_spawn_farmers = []
        # Now, spawn as many farmers as possible with the remaining wheat
        max_spawn_farmers = min(len(remaining_farmers) // 2, wheat // 10) if wheat >= 10 else 0
        if max_spawn_farmers > 0:
            to_spawn_farmers = remaining_farmers[: max_spawn_farmers * 2]
            remaining_farmers = remaining_farmers[max_spawn_farmers * 2 :]

        # Assign groups
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        for f in to_spawn_farmers:
            environment.assign_group(f, "spawn farmer")

        for f in to_spawn_warriors:
            environment.assign_group(f, "spawn warrior")

        # Note: If there were leftover farmers after the above, they would have been assigned to "farm".
        # This respects the rule that every component is assigned to exactly one group.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Distribute villagers in the cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village (Farmers should return to Village)
        """
        for c in components:
            role = getattr(c, "role", None)

            if role == "Warrior":
                # Warriors should stay in cave to attack
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                # Farmers should go back to Village
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave
                environment.assign_group(c, "cave")