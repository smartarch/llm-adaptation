from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Put all Warriors into the Cave (to be ready to attack)
        # - Use at most two Farmers for "spawn farmer" (if enough Farmers and wheat)
        # - Use at most two Farmers for "spawn warrior" (if enough Farmers left and wheat)
        # - Remaining Farmers stay in farming
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: all farmers farm, all warriors go to cave
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Read current wheat (robust to missing data)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn farmer: need at least 4 farmers and wheat >= 10
        spawn_farm = []
        if len(farmers) >= 4 and wheat >= 10:
            spawn_farm = farmers[:2]
            for c in spawn_farm:
                environment.assign_group(c, "spawn farmer")

        # Spawn warrior: use two additional farmers if available and wheat >= 12
        remaining_for_war_spawn = [f for f in farmers if f not in spawn_farm]  # farmers left after faction spawn
        spawn_war = []
        if len(remaining_for_war_spawn) >= 2 and wheat >= 12:
            spawn_war = remaining_for_war_spawn[:2]
            for c in spawn_war:
                environment.assign_group(c, "spawn warrior")

        # Others (not in spawns) remain as initially assigned:
        # - Farmers not in spawn_farm stay in "farm"
        # - Farmers in spawn_war are already set to "spawn warrior"
        # - Warriors remain in "cave" (already set)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")