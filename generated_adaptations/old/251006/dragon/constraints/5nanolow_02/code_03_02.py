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

        # Greedy spawning:
        # First, spawn as many Warriors as possible using pairs of farmers and 12 wheat each
        to_spawn_warriors = []
        remaining_farmers = farmers[:]

        while len(remaining_farmers) >= 2 and wheat >= 12:
            # Use two farmers to spawn one Warrior
            to_spawn_warriors = remaining_farmers[:2]
            remaining_farmers = remaining_farmers[2:]
            wheat -= 12
            # Note: The two farmers used for spawning are not automatically assigned yet;
            # we assign them to "spawn warrior" below.

            # Apply the spawn immediately to avoid re-splitting in the loop
            for f in to_spawn_warriors:
                environment.assign_group(f, "spawn warrior")
            to_spawn_warriors = []

        # After warrior spawns, spawn as many farmers as possible with remaining wheat
        to_spawn_farmers = []
        if len(remaining_farmers) >= 2 and wheat >= 10:
            max_spawn_farmers = min(len(remaining_farmers) // 2, wheat // 10)
            if max_spawn_farmers > 0:
                to_spawn_farmers = remaining_farmers[: max_spawn_farmers * 2]
                remaining_farmers = remaining_farmers[max_spawn_farmers * 2 :]
                wheat -= max_spawn_farmers * 10
                for f in to_spawn_farmers:
                    environment.assign_group(f, "spawn farmer")

        # The rest go to farming
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        # Note: If there were any farmers that were used for spawning but not in the remaining pool,
        # they've already been assigned to "spawn warrior" or "spawn farmer" above.

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