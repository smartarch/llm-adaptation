"""
Reasoning and updated adaptation strategy (embedded as comments in this code block):

- Goal: Ensure every village component is assigned exactly once per village-step without duplicates,
  while actively promoting spawning of new villagers and focusing combat strengths on the Dragon.

Key updates to strategy:
- Robust assignment tracking: Use an internal guard (based on object id) to ensure no component is assigned more than once per call to assign_in_village or assign_in_cave.
- Spawn logic correctness: Maintain the intended spawn policy
  - In village, Farmers are the source for spawning: for every 2 farmers in the "spawn farmer" group and 10 wheat, a new Farmer is spawned.
  - For Warriors, the "spawn warrior" group uses the same rule with 12 wheat per pair.
  - We compute the number of pairs (floor(group_size / 2)) subject to wheat constraints, then allocate 2*pairs villagers to the corresponding spawn group and the rest to farm.
  - This ensures the number of new villagers spawned matches the environmental policy.
- All Warriors should go to the Cave, all Farmers should stay in the Village (or spawn), as required.
- In the cave, Warriors should attack the Dragon and Farmers should head back to the Village.
- Fallback: If any component remains unassigned due to edge cases, assign it to a safe default group to avoid assignment errors.

This implementation aims to fix:
- No repeated assignments within a single assignment call.
- Ensuring at least some Warriors are spawned when feasible (by respecting the spawn rules and resource constraints).
- Guaranteeing that every component gets exactly one group assignment per step.
"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Guard to prevent multiple assignments of the same component in this method
        assigned_ids = set()

        def assign_once(component, group_id):
            if id(component) in assigned_ids:
                return
            environment.assign_group(component, group_id)
            assigned_ids.add(id(component))

        # Split villagers by role (read-only attributes)
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_village = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)

        # Wheat available on the Farm (default to 0 if not present)
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0) or 0

        # Determine how many spawns we can perform this step
        max_spawn_farmers = min(F // 2, wheat // 10)
        num_spawn_farmers = 2 * max_spawn_farmers

        remaining_wheat_after_farm_spawns = wheat - num_spawn_farmers * 10
        remaining_farmers = F - num_spawn_farmers

        max_spawn_warriors = min(remaining_farmers // 2, remaining_wheat_after_farm_spawns // 12)
        num_spawn_warriors = 2 * max_spawn_warriors

        # Slicing farmers into spawn groups and farm group
        farmers_list = farmers
        spawn_farmer_group_members = farmers_list[:num_spawn_farmers]
        spawn_warrior_group_members = farmers_list[num_spawn_farmers:num_spawn_farmers + num_spawn_warriors]
        remaining_farmers_for_farm = farmers_list[num_spawn_farmers + num_spawn_warriors:]

        # Assign groups for farmers
        for c in spawn_farmer_group_members:
            assign_once(c, "spawn farmer")
        for c in spawn_warrior_group_members:
            assign_once(c, "spawn warrior")
        for c in remaining_farmers_for_farm:
            assign_once(c, "farm")

        # Warriors in village go to cave
        for w in warriors_in_village:
            assign_once(w, "cave")

        # Fallback: assign any unassigned components to a safe default ("farm")
        for c in components:
            if id(c) not in assigned_ids:
                assign_once(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Guard to prevent multiple assignments of the same component in this method
        assigned_ids = set()

        def assign_once(component, group_id):
            if id(component) in assigned_ids:
                return
            environment.assign_group(component, group_id)
            assigned_ids.add(id(component))

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                assign_once(c, "attack")
            else:
                assign_once(c, "village")

        # Ensure all components get an assignment (fallback)
        for c in components:
            if id(c) not in assigned_ids:
                # Default to going to village if not already assigned
                assign_once(c, "village")