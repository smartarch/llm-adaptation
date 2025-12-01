from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # In Village: move Warriors to cave, manage spawning in a way that prioritizes early Warrior spawns.
        farmers = []
        warrior_count = 0

        # Separate villagers by role; move Warriors to cave immediately.
        for comp in components:
            role = getattr(comp, "role", None)
            role_str = str(role).lower() if role is not None else ""
            if role_str == "warrior":
                environment.assign_group(comp, "cave")
                warrior_count += 1
            else:
                # Treat as Farmer (default)
                farmers.append(comp)

        # Determine available wheat in the Farm
        wheat_here = 0
        farm = getattr(environment, "farm", None)
        if farm is not None:
            wheat_here = getattr(farm, "wheat", 0)

        # Spawn plan:
        # 1) Warrior spawns: as many as possible given two-villager-per-spawn and 12 wheat per spawn
        # 2) Farmer spawns: use remaining villagers and wheat (10 wheat per spawn)
        n_farmers = len(farmers)
        spawns_warriors = 0
        spawns_farmers = 0

        if n_farmers >= 2 and wheat_here >= 12:
            max_by_villagers = n_farmers // 2
            max_by_wheat = wheat_here // 12
            spawns_warriors = min(max_by_villagers, max_by_wheat)

        # Update wheat after Warrior spawns
        wheat_after_warriors = wheat_here - (spawns_warriors * 12)
        remaining_farmers_for_spawns = n_farmers - (2 * spawns_warriors)

        if remaining_farmers_for_spawns >= 2 and wheat_after_warriors >= 10:
            max_by_villagers = remaining_farmers_for_spawns // 2
            max_by_wheat = wheat_after_warriors // 10
            spawns_farmers = min(max_by_villagers, max_by_wheat)

        # Assign groups for farmers based on spawn plan:
        # First 2*spawns_warriors farmers -> "spawn warrior"
        # Next 2*spawns_farmers farmers -> "spawn farmer"
        # Remaining farmers -> "farm"
        total_farmers = n_farmers
        for idx, comp in enumerate(farmers):
            if idx < 2 * spawns_warriors:
                environment.assign_group(comp, "spawn warrior")
            elif idx < 2 * spawns_warriors + 2 * spawns_farmers:
                environment.assign_group(comp, "spawn farmer")
            else:
                environment.assign_group(comp, "farm")

        # Edge case: if there are no farmers, nothing else to do.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors attack the Dragon; Farmers go back to Village
        for comp in components:
            role = getattr(comp, "role", None)
            role_str = str(role).lower() if role is not None else ""
            if role_str == "warrior":
                environment.assign_group(comp, "attack")
            else:
                environment.assign_group(comp, "village")