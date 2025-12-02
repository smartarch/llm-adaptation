from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farm_id = "farm"
        cave_id = "cave"
        spawn_farm_id = "spawn farmer"
        spawn_war_id = "spawn warrior"

        # Separate farmers and warriors among villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All warriors should head to the Cave (to attack in the next phase)
        for c in warriors:
            environment.assign_group(c, cave_id)

        # 2) Manage farmers: attempt to spawn new villagers if resources allow, else farm
        available = list(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Try to spawn a Warrior if we have at least 12 wheat and at least 2 farmers available
        if len(available) >= 2 and wheat >= 12:
            for _ in range(2):
                if not available:
                    break
                c = available.pop(0)
                environment.assign_group(c, spawn_war_id)

        # Recompute wheat (in case the engine consumed wheat this step)
        wheat = getattr(environment.farm, "wheat", 0)

        # Try to spawn a Farmer if we have at least 10 wheat and at least 2 farmers remaining
        if len(available) >= 2 and wheat >= 10:
            for _ in range(2):
                if not available:
                    break
                c = available.pop(0)
                environment.assign_group(c, spawn_farm_id)

        # Remaining farmers stay in the Village and farm
        for c in available:
            environment.assign_group(c, farm_id)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attack_id = "attack"
        cave_id = "cave"
        village_id = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # Warriors attack the Dragon
                environment.assign_group(c, attack_id)
            else:
                # Farmers go back to the Village
                environment.assign_group(c, village_id)