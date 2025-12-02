import abc

# The base class is assumed to be importable as described
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": Farmers who will farm
        - "cave": Warriors who will go to cave
        - "spawn farmer": Farmers grouped here to spawn new Farmers
        - "spawn warrior": (optional) for spawning Warriors if wheat allows
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Ensure all Warriors go to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers stay in Village by default
        for f in farmers:
            environment.assign_group(f, "farm")

        # Compute how many spawns of farmers we can do
        # Wheat required: 10 per spawned farmer (per two villagers in the spawn group)
        # Spawn requires two villagers in the group
        wheat_available = getattr(environment.farm, "wheat", 0)

        max_spawns_by_wheat = wheat_available // 10

        # Number of farmers available to form spawn farmer group
        num_farmers = len(farmers)
        max_spawns_by_villagers = num_farmers // 2

        max_spawns = min(max_spawns_by_wheat, max_spawns_by_villagers)

        # Determine how many farmers to assign to the spawn farmer group
        spawn_farmers_count = max_spawns * 2
        if spawn_farmers_count > 0:
            # Move the first N farmers to the spawn farmer group
            for i, f in enumerate(farmers):
                if i < spawn_farmers_count:
                    environment.assign_group(f, "spawn farmer")
                else:
                    # The rest stay farming
                    environment.assign_group(f, "farm")
        # If no spawns, farmers remain in farm group (already set)

        # Note: We do not explicitly assign anyone to "spawn warrior" here, but if you
        # want to aggressively spawn Warriors, you could implement a similar logic
        # using remaining wheat, ensuring you still have enough villagers in the
        # spawn warrior group (two per spawn). For simplicity and readability,
        # we focus on farming spawns to increase population.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Warriors that will attack the Dragon
        - "cave": Stay in the Cave (could be used if some villagers stay)
        - "village": Go to the Village (Farmers should stay in Village per strategy)
        """
        # Warriors should attack the Dragon
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")

        # Farmers should go to the Village
        for c in components:
            if getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "village")

        # Optionally, you can place some villagers in "cave" if you want to keep some
        # villagers in cave without attacking, but per strategy we keep them in village.