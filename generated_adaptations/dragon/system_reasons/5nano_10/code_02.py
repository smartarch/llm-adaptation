from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors among villagers in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Final group mapping (one group per component in this step)
        # We will compute spawn allocations first, then assign remaining to farming.
        # We must ensure all Warriors go to the cave (we set them to "cave" here),
        # and Farmers stay in the Village (default to "farm" unless chosen for spawning).

        # Start by scheduling default allocations
        for f in farmers:
            environment.assign_group(f, "farm")
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning logic (one step, exclusive groups per villager)
        # Use wheat budget to decide spawn pairs
        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Number of farmer spawn pairs we can attempt this step
        max_farm_pairs_by_wheat = available_wheat // 10 if available_wheat >= 10 else 0
        max_farm_pairs_by_count = len(farmers) // 2
        sp_farm_pairs = min(2, max_farm_pairs_by_wheat, max_farm_pairs_by_count)

        # Wheat budget after allocating farmer spawns
        wheat_after_farm_spawns = max(0, available_wheat - sp_farm_pairs * 10)

        # Remaining farmers after farmer-spawn allocations
        used_for_farm_spawns = sp_farm_pairs * 2
        remaining_farmers_for_war_spawn = len(farmers) - used_for_farm_spawns

        # Number of warrior spawn pairs we can attempt this step
        max_war_pairs_by_wheat = wheat_after_farm_spawns // 12 if wheat_after_farm_spawns >= 12 else 0
        sp_war_pairs = min(2, max_war_pairs_by_wheat, remaining_farmers_for_war_spawn // 2)

        # Now assign specific farmers to spawn groups
        idx = 0

        # Assign first 2*sp_farm_pairs farmers to "spawn farmer"
        for _ in range(sp_farm_pairs * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Assign next 2*sp_war_pairs farmers to "spawn warrior"
        for _ in range(sp_war_pairs * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers (if any) stay in the village to farm
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Warriors already set to "cave" above; nothing else to do for them here.

        # Note: The actual spawning consumes wheat inside the environment/game rules.


    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack, Farmers return to the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors attack
        for w in warriors:
            environment.assign_group(w, "attack")

        # Farmers go back to the Village
        for f in farmers:
            environment.assign_group(f, "village")