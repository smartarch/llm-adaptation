from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Villagers in Village: decide who farms, who goes to Cave, and who spawns
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Read current wheat (robust to missing data)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # 1) Spawn farmer: need at least 2 farmers and wheat >= 10
        spawn_farmer = []
        if len(farmers) >= 2 and wheat >= 10:
            spawn_farmer = farmers[:2]
            for c in spawn_farmer:
                environment.assign_group(c, "spawn farmer")

        # Remaining farmers go to farming
        for c in farmers:
            if c in spawn_farmer:
                continue
            environment.assign_group(c, "farm")

        # 2) Spawn warrior: require at least 4 warriors (including those not used for farmer spawn)
        remaining_warriors = [w for w in warriors if w not in spawn_farmer]
        spawn_warrior = []
        if len(remaining_warriors) >= 4 and wheat >= 12:
            spawn_warrior = remaining_warriors[:2]
            for c in spawn_warrior:
                environment.assign_group(c, "spawn warrior")

        # Remaining warriors (not spawning) should head to the Cave
        for c in remaining_warriors:
            if c not in spawn_warrior:
                environment.assign_group(c, "cave")

        # Farmers that were not assigned to spawn (or farm) are already handled above.
        # If there are any edge cases, they will be re-evaluated in subsequent steps.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")