from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # In Village: move Warriors to cave, keep Farmers here, but optionally spawn new villagers.
        # First, assign all Warriors to the cave group (to go attack later).
        farmers = []
        warrior_count = 0

        for comp in components:
            role = str(getattr(comp, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(comp, "cave")
                warrior_count += 1
            else:  # assume Farmer
                farmers.append(comp)

        # Determine available wheat (default 0 if farm not present)
        wheat_here = 0
        farm = getattr(environment, "farm", None)
        if farm is not None:
            wheat_here = getattr(farm, "wheat", 0)

        # Spawning plan:
        # - We can spawn at most floor(len(farmers) / 2) Farmers (two per spawn)
        # - We can spawn at most floor(wheat_here / 10) Farmers (10 wheat per Farmer-spawn)
        # - Then with remaining farmers (two-villager pairs) we can spawn Warriors (12 wheat per Warrior-spawn)
        spawns_farmers = 0
        spawns_warriors = 0

        n_farmers = len(farmers)

        if n_farmers >= 2 and wheat_here >= 10:
            max_by_villagers = n_farmers // 2
            max_by_wheat = wheat_here // 10
            spawns_farmers = min(max_by_villagers, max_by_wheat)

        # Update remaining wheat after farmer spawns
        wheat_after_farm_spawns = wheat_here - (spawns_farmers * 10)
        remaining_farmers_for_warrior_spawns = n_farmers - (2 * spawns_farmers)

        if remaining_farmers_for_warrior_spawns >= 2 and wheat_after_farm_spawns >= 12:
            max_by_villagers = remaining_farmers_for_warrior_spawns // 2
            max_by_wheat = wheat_after_farm_spawns // 12
            spawns_warriors = min(max_by_villagers, max_by_wheat)

        # Assign farmers to proper spawn groups or farming
        total_farmers = len(farmers)
        for idx, comp in enumerate(farmers):
            if idx < 2 * spawns_farmers:
                environment.assign_group(comp, "spawn farmer")
            elif idx < 2 * spawns_farmers + 2 * spawns_warriors:
                environment.assign_group(comp, "spawn warrior")
            else:
                environment.assign_group(comp, "farm")

        # Note: If no farmers exist, nothing further to do.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors should attack the Dragon; Farmers should go back to Village.
        for comp in components:
            role = str(getattr(comp, "role", "")).lower()
            if role == "warrior":
                environment.assign_group(comp, "attack")
            else:  # Farmer
                environment.assign_group(comp, "village")