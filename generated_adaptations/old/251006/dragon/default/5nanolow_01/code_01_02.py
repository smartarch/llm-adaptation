import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Default clean slate: assign farmers to farm, warriors to cave
        farmers = []
        warriors = []
        others = []  # just in case

        for c in components:
            if getattr(c, "role", None) == "Farmer":
                farmers.append(c)
            elif getattr(c, "role", None) == "Warrior":
                warriors.append(c)
            else:
                others.append(c)

        # 1) Farmers -> stay in village, "farm" group
        for f in farmers:
            environment.assign_group(f, "farm")

        # 2) Warriors -> go to cave (they will attack from the cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 3) Spawn planning:
        # Use wheat to spawn as many as possible, prioritizing farmers then warriors.
        # We will assume we can move 2 villagers into a spawn group to trigger spawns.
        # Number of pairs we can spawn for farmers: floor(wheat/10) and need 2 per pair
        # Number of pairs we can spawn for warriors: floor(wheat/12) and need 2 per pair
        wheat = 0
        try:
            wheat = int(getattr(environment.farm, "wheat", 0))
        except Exception:
            wheat = 0

        # We must consider only villagers that are currently in village (farmers + warriors)
        # For spawning, we will choose from farmers first, then from warriors (both currently assigned to their default groups)
        # We'll compute how many pairs we can spawn given wheat
        max_pairs_farmers = min(len(farmers) // 2, wheat // 10) if wheat >= 10 else 0
        # Update wheat consumption logically: we will assume spawning consumes wheat, not updated in components here
        remaining_wheat_after_farm_spawns = max(0, wheat - max_pairs_farmers * 10)

        max_pairs_warriors = min(len(warriors) // 2, remaining_wheat_after_farm_spawns // 12) if remaining_wheat_after_farm_spawns >= 12 else 0

        # Assign 2*pairs for each to the respective spawn groups
        # First, farmers to "spawn farmer"
        farmers_to_spawn = 2 * max_pairs_farmers
        spawned_farmers = 0
        if farmers_to_spawn > 0:
            for i in range(min(farmers_to_spawn, len(farmers))):
                # Move the first N farmers to spawn farmer until exhausted
                f = farmers[i]
                if i < farmers_to_spawn:
                    environment.assign_group(f, "spawn farmer")
                    spawned_farmers += 1
            # Note: the actual list of farmers for next steps is unchanged; we won't reassign the rest

        # Then, warriors to "spawn warrior"
        warriors_to_spawn = 2 * max_pairs_warriors
        if warriors_to_spawn > 0:
            for i in range(min(warriors_to_spawn, len(warriors))):
                w = warriors[i]
                if i < warriors_to_spawn:
                    environment.assign_group(w, "spawn warrior")

        # Remaining villagers (not assigned to spawn groups) stay in their default groups
        # This ensures all components are assigned to some group:
        # Farmers already assigned to "farm" earlier
        # Warriors already assigned to "cave" earlier
        # Spawn groups have been assigned for the chosen subset

        # Note: If a component has already been assigned via prior steps, re-assigning here would override.
        # The above logic ensures explicit assignments for all components in this phase.

        # Ensure that special groups exist in group_ids: we rely on the environment to accept these IDs.


    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: assign all Warriors to attack, all others can stay or move to village as needed
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Non-warriors in cave: either stay in cave or move to village
                # We'll keep Farmers that were in cave to "cave" and non-warriors to "cave" as a fallback,
                # but the instruction says "All Warriors should go to the Cave, and then attack the Dragon."
                # We'll keep non-Warriors in "cave" if they are already there; otherwise move them to "cave" to keep them close.
                environment.assign_group(c, "cave")
        # Additionally, allow a path to village for flexibility (not strictly required)
        # If some villagers are intended to move to village, you can uncomment the following lines:
        # for c in components:
        #     environment.assign_group(c, "village")