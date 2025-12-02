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

        # 1) Assign all Warriors to go to Cave (they will attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village: split into farming and spawning
        num_farmers = len(farmers)

        # Wheat available for spawning
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Compute potential spawns
        max_spawn_farmers = min(num_farmers // 2, wheat // 10) if wheat >= 10 else 0
        spawn_farmers_count = max_spawn_farmers * 2  # number of farmers going to spawn farmer group
        remaining_farmers = farmers[:]

        # Decide how many from farmers to allocate to spawn warrior group
        # Requires 12 wheat per 2 villagers in that group -> per 2 villagers consuming 12 wheat.
        max_spawn_warriors = min(len(remaining_farmers) // 2, (wheat - max_spawn_farmers * 10) // 12) if wheat - max_spawn_farmers * 10 >= 12 else 0
        spawn_warriors_count = max_spawn_warriors * 2

        # Remove those to be spawned for warriors from the pool
        to_spawn_warriors = remaining_farmers[:spawn_warriors_count]
        remaining_farmers = remaining_farmers[spawn_warriors_count:]

        # Remove those to be spawned for farmers from the pool (but keep count for group)
        to_spawn_farmers = remaining_farmers[:spawn_farmers_count]
        remaining_farmers = remaining_farmers[spawn_farmers_count:]

        # Assign groups
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        for f in to_spawn_farmers:
            environment.assign_group(f, "spawn farmer")

        for f in to_spawn_warriors:
            environment.assign_group(f, "spawn warrior")

        # Note: If no Warriors were in village to begin with, Warriors can still be spawned from Farmers.
        # The existing Warriors (in cave) remain unaffected.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Distribute villagers in the cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village (Farmers should return to Village)
        """
        # Assign based on role; this ensures consistent behavior
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