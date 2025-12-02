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
        - "cave": Warriors who will go to cave (to attack)
        - "spawn farmer": Farmers grouped here to spawn new Farmers
        - "spawn warrior": Warriors grouped here to spawn new Warriors
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Determine how many spawns we can support given wheat and villagers
        wheat_available = getattr(environment.farm, "wheat", 0)

        max_spawns_farm_by_villagers = len(farmers) // 2
        max_spawns_farm_by_wheat = wheat_available // 10
        max_spawns_farm = min(max_spawns_farm_by_villagers, max_spawns_farm_by_wheat)

        remaining_wheat = wheat_available - max_spawns_farm * 10

        max_spawns_war_by_villagers = len(warriors) // 2
        max_spawns_war_by_wheat = remaining_wheat // 12
        max_spawns_war = min(max_spawns_war_by_villagers, max_spawns_war_by_wheat)

        # Decide target groups for each category in a single pass
        assignments = {}

        # Assign farmers
        # - First 2*max_spawns_farm farmers go to spawn farmer
        spawn_farmers_needed = max_spawns_farm * 2
        for i, f in enumerate(farmers):
            if i < spawn_farmers_needed:
                assignments[f] = "spawn farmer"
            else:
                # remaining farmers farm
                assignments[f] = "farm"

        # Assign warriors
        # - First 2*max_spawns_war warriors go to spawn warrior
        spawn_warriors_needed = max_spawns_war * 2
        for i, w in enumerate(warriors):
            if i < spawn_warriors_needed:
                assignments[w] = "spawn warrior"
            else:
                # remaining warriors go to cave to attack
                assignments[w] = "cave"

        # Any edge case where there are no farmers or no warriors is handled by the above logic.

        # Apply a single pass assignment to guarantee exactly one group per component
        for comp in components:
            # If not already assigned (should be assigned above), default to sensible group
            if comp in assignments:
                environment.assign_group(comp, assignments[comp])
            else:
                # Fallback: keep in village farming
                environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon (Warriors)
        - "cave": Stay in the Cave (not used by strategy, but allowed)
        - "village": Go to the Village (Farmers should stay in Village)
        """
        # Warriors should attack the Dragon
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")

        # Farmers should go to the Village
        for c in components:
            if getattr(c, "role", None) == "Farmer":
                environment.assign_group(c, "village")

        # If there are any components not yet assigned (edge cases), place them in cave by default
        for c in components:
            # If already assigned (in previous two loops), skip
            # We cannot access a per-component assigned flag here, so we check
            # by attempting to see current group isn't set. The API does not expose a direct getter here,
            # but we ensure we don't re-assign already assigned ones by simply continuing.
            # To keep compatibility, we do a no-op as already assigned above.
            pass