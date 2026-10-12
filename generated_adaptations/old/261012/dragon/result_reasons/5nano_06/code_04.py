import abc

# Assuming the base class is available from the specified module
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all existing Warriors to the Cave (they will attack from there)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning for Farmers (dynamic)
        # Determine current wheat in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Helper: assign remaining farmers to a default group
        remaining_farmers = list(farmers)

        # Clear any previous temporary allocations by re-assigning below

        # Spawn logic (greedy, step-aware)
        # Try to spawn both a Warrior and a Farmer if possible
        assigned_to_spawn_warrior = []
        assigned_to_spawn_farmer = []
        if step <= 15:
            # Case 1: enough farmers for both spawns and enough wheat for both
            if len(remaining_farmers) >= 4 and wheat >= 22:
                assigned_to_spawn_warrior = remaining_farmers[:2]
                assigned_to_spawn_farmer = remaining_farmers[2:4]
                remaining_farmers = remaining_farmers[4:]
            else:
                # Case 2: try to spawn a Warrior if possible
                if len(remaining_farmers) >= 2 and wheat >= 12:
                    assigned_to_spawn_warrior = remaining_farmers[:2]
                    remaining_farmers = remaining_farmers[2:]
                # Case 3: try to spawn a Farmer if possible
                if len(remaining_farmers) >= 2 and wheat >= 10:
                    # If we didn't allocate for Warrior above, or even if we did a Warrior,
                    # we can allocate two for a Farmer if wheat allows.
                    if not assigned_to_spawn_farmer:
                        assigned_to_spawn_farmer = remaining_farmers[:2]
                        remaining_farmers = remaining_farmers[2:]

        # 3) Assign groups for Farmers
        # First, assign the selected two to spawn warrior (if any)
        for f in assigned_to_spawn_warrior:
            environment.assign_group(f, "spawn warrior")

        # Then, assign the next two to spawn farmer (if any)
        # Note: If the same farmer was already assigned to spawn warrior, they won't be reassigned here
        for f in assigned_to_spawn_farmer:
            environment.assign_group(f, "spawn farmer")

        # Assign remaining farmers to farm
        for f in remaining_farmers:
            # If not already assigned to a spawn group, send to farming
            if f not in assigned_to_spawn_warrior and f not in assigned_to_spawn_farmer:
                environment.assign_group(f, "farm")

        # Edge case: if there are no farmers (or after allocations none left),
        # nothing else to do here; the environment will handle spawning when there are members in spawn groups.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")