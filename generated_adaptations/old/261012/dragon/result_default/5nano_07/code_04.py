from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (for Warriors to attack later)
        - spawn farmer: for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers in this group and 12 wheat, a new Warrior is spawned
        Strategy:
        - Spawn Warriors first (to maximize early DPS), using 2 farmers per Warrior spawn and 12 wheat per pair.
        - Then spawn Farmers with any remaining Wheat/Farmers.
        - Remaining Farmers go to farming.
        """
        # Classify current farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        n_farmers = len(farmers)

        # Wheat available for spawning
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Phase 1: determine how many Warrior spawns we can trigger this step
        warrior_spawns = min(n_farmers // 2, wheat // 12)
        # Remaining farmers after Warrior spawns
        remaining_farmers_after_warriors = n_farmers - 2 * warrior_spawns
        wheat_after_warriors = max(0, wheat - 12 * warrior_spawns)

        # Phase 2: determine how many Farmer spawns we can trigger with remaining resources
        farmer_spawns = min(remaining_farmers_after_warriors // 2, wheat_after_warriors // 10)
        # Sizes for quick checks (2 per spawn)
        warrior_spawn_size = 2 * warrior_spawns
        farmer_spawn_size = 2 * farmer_spawns

        # Assign in input order
        farmer_index = 0
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors go to the Cave
                environment.assign_group(c, "cave")
            else:
                # Farmers: allocate to spawn warrior first, then spawn farmer, then farm
                if farmer_index < warrior_spawn_size:
                    environment.assign_group(c, "spawn warrior")
                elif farmer_index < warrior_spawn_size + farmer_spawn_size:
                    environment.assign_group(c, "spawn farmer")
                else:
                    environment.assign_group(c, "farm")
                farmer_index += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")