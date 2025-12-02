from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning plan using Farmers only (Warriors are not available in village due to step 1)
        n_farmers = len(farmers)
        wheat = 0
        # Safely access environment.farm.wheat
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Maximum number of "spawn farmer" actions we can support
        spf = min(n_farmers // 2, wheat // 10)
        spf2 = spf * 2  # number of farmers allocated to "spawn farmer"

        remaining_farmers_after_farmer_spawns = n_farmers - spf2
        remaining_wheat_after_farmer_spawns = wheat - spf * 10

        # Maximum number of "spawn warrior" actions we can support with remaining farmers and wheat
        swpawns = min(remaining_farmers_after_farmer_spawns // 2,
                       remaining_wheat_after_farmer_spawns // 12)
        spw2 = swpawns * 2  # number of farmers allocated to "spawn warrior"

        # Allocate farmers in a deterministic order:
        # - first 2*spf to "spawn farmer"
        # - next 2*swpawns to "spawn warrior"
        # - the rest to "farm"
        for idx, f in enumerate(farmers):
            if idx < spf2:
                environment.assign_group(f, "spawn farmer")
            elif idx < spf2 + spw2:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack, Farmers back to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")