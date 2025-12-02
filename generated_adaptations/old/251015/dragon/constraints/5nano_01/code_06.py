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
        # Prefer at least one Warrior spawn (requires 2 farmers and 12 wheat).
        # If not possible, fall back to spawning Farmers based on available wheat.
        num_spawn_warriors = 0  # count of Warrior-spawn groups (each uses 2 farmers)
        num_spawn_farmers = 0   # count of Farmer-spawn groups (each uses 2 farmers)

        if F >= 2 and wheat >= 12:
            # Reserve 2 farmers for a Warrior spawn
            num_spawn_warriors = 1
            rem_farmers = F - 2
            rem_wheat = wheat - 12
            max_far_spawns = min(rem_farmers // 2, rem_wheat // 10)
            num_spawn_farmers = max_far_spawns * 2
        else:
            max_far_spawns = min(F // 2, wheat // 10)
            num_spawn_farmers = max_far_spawns * 2
            rem_farmers = F - num_spawn_farmers
            rem_wheat = wheat - num_spawn_farmers * 10
            max_war_spawns = min(rem_farmers // 2, rem_wheat // 12)
            num_spawn_warriors = max_war_spawns * 2

        farmers_list = farmers
        spawn_farmer_group_members = farmers_list[:num_spawn_farmers]
        spawn_warrior_group_members = farmers_list[num_spawn_farmers:num_spawn_farmers + num_spawn_warriors]
        remaining_farmers_for_farm = farmers_list[num_spawn_farmers + num_spawn_warriors:]

        for c in spawn_farmer_group_members:
            assign_once(c, "spawn farmer")
        for c in spawn_warrior_group_members:
            assign_once(c, "spawn warrior")
        for c in remaining_farmers_for_farm:
            assign_once(c, "farm")

        # All Warriors should go to the Cave
        for w in warriors_in_village:
            assign_once(w, "cave")

        # Safety net: assign any unassigned component to a safe default
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

        # Safety net: ensure every component is assigned
        for c in components:
            if id(c) not in assigned:
                assign_once(c, "village")