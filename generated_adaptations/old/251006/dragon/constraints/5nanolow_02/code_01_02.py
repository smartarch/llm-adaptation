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
        # - Everything not assigned yet defaults to farm if Farmer
        # - We'll compute how many farmers can spawn
        num_farmers = len(farmers)
        if num_farmers == 0:
            # Nothing to do for farmers
            return

        # Wheat available for spawning
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        max_spawn_farmers = min(num_farmers // 2, wheat // 10) if wheat >= 10 else 0
        spawn_farmers_count = max_spawn_farmers * 2
        remain_farmers = farmers[:]

        # First, assign farmers to spawn farmer group (2 per new farmer spawned)
        to_spawn_farmers = []
        if spawn_farmers_count > 0:
            to_spawn_farmers = remain_farmers[:spawn_farmers_count]
            remain_farmers = remain_farmers[spawn_farmers_count:]

        # Assign groups
        for f in remain_farmers:
            environment.assign_group(f, "farm")

        for f in to_spawn_farmers:
            environment.assign_group(f, "spawn farmer")

        # Note: We leave "spawn warrior" group empty for simplicity, since we primarily
        # want to ensure Warriors are in cave and Farmers can farm or spawn as possible.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Distribute villagers in the cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village (Farmers should return to Village)
        """
        # Separate by role
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