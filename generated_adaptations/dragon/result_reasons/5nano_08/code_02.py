from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - "farm": stay in village and farm
        - "cave": go to the Cave (for Warriors only, per strategy)
        - "spawn farmer": for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - "spawn warrior": for every two villagers in this group and 12 wheat, a new Warrior is spawned
        """
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # We will build a map: component -> target_group
        assignments = {}

        # Default: farmers stay in village and farm
        for f in farmers:
            assignments[f] = "farm"

        # Move all Warriors to the Cave (they will attack from the cave)
        for w in warriors:
            assignments[w] = "cave"

        # Decide on spawning farmers/warriors (use wheat when possible)
        # Try to spawn both a farmer and a warrior if we have enough farmers and enough wheat.
        to_spawn_farmer = []
        to_spawn_warrior = []

        if len(farmers) >= 4 and wheat >= 22:
            # Use four farmers: two for each spawn type
            to_spawn_farmer = farmers[:2]
            to_spawn_warrior = farmers[2:4]
        else:
            # Try to spawn at least one farmer if possible
            if len(farmers) >= 2 and wheat >= 10:
                to_spawn_farmer = farmers[:2]
            # Try to spawn at least one warrior if possible (don't reuse the same two)
            if len(farmers) >= 4 and wheat >= 12:
                to_spawn_warrior = farmers[2:4]

        for f in to_spawn_farmer:
            assignments[f] = "spawn farmer"
        for f in to_spawn_warrior:
            if f not in to_spawn_farmer:
                assignments[f] = "spawn warrior"

        # Apply assignments to environment (one assignment per villager)
        for c, g in assignments.items():
            environment.assign_group(c, g)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to:
        - "attack": Attack the Dragon (all Warriors)
        - "cave": Stay in the Cave (if any non-Warriors end up here)
        - "village": Go to the Village (Farmers return to farm)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")