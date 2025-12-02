from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign_once(component, group_id):
            if id(component) in assigned:
                return
            environment.assign_group(component, group_id)
            assigned.add(id(component))

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_village = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)

        # Wheat available on the Farm
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0) or 0

        # Spawn strategy:
        # 1) If possible, spawn one warrior pair (requires 2 farmers and 12 wheat)
        # 2) With remaining resources, spawn as many farmer pairs as possible (each pair needs 2 farmers and 10 wheat)
        num_spawn_warriors = 0  # number of warrior-spawn groups (each group corresponds to 2 villagers)
        num_spawn_farmers = 0   # number of farmer-spawn groups (each group corresponds to 2 villagers)

        if F >= 2 and wheat >= 12:
            num_spawn_warriors = 1  # one warrior spawn consumes 2 farmers
            F_rem = F - 2
            W_rem = wheat - 12
        else:
            F_rem = F
            W_rem = wheat

        max_far_spawns = min(F_rem // 2, W_rem // 10)
        num_spawn_farmers = max_far_spawns  # number of pairs; each pair implies 2 farmers

        # Gather members for each spawn/group
        spawn_farmer_group_members = farmers[:num_spawn_farmers * 2]
        spawn_warrior_group_members = farmers[num_spawn_farmers * 2:num_spawn_farmers * 2 + (2 * num_spawn_warriors)]
        remaining_farmers_for_farm = farmers[num_spawn_farmers * 2 + (2 * num_spawn_warriors):]

        # Assign groups for farmers
        for c in spawn_farmer_group_members:
            assign_once(c, "spawn farmer")
        for c in spawn_warrior_group_members:
            assign_once(c, "spawn warrior")
        for c in remaining_farmers_for_farm:
            assign_once(c, "farm")

        # All Warriors should go to the Cave
        for w in warriors_in_village:
            assign_once(w, "cave")

        # Safety: assign any unassigned components to a safe default (farm)
        for c in components:
            if id(c) not in assigned:
                assign_once(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign_once(component, group_id):
            if id(component) in assigned:
                return
            environment.assign_group(component, group_id)
            assigned.add(id(component))

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                assign_once(c, "attack")
            else:
                assign_once(c, "village")

        # No extra fallback to avoid duplicate assignments