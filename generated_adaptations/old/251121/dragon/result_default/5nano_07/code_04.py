from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All warriors should go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        if F == 0:
            # Nothing else to do
            return

        # Wheat available for spawning
        W = getattr(environment.farm, "wheat", 0)

        # 2) Keep at least some farmers farming to maintain wheat production
        # We choose to keep at least 1 farmer farming
        base_farm_count = max(1, F - 1)

        # Farmers available for spawning (in addition to those kept farming)
        spawn_pool = F - base_farm_count

        # Greedy spawning plan:
        #  - First spawn as many Warriors as possible (cost 12 wheat each)
        #  - Then spawn as many Farmers as possible (cost 10 wheat each)
        max_war_spawns = 0
        max_farm_spawns = 0

        if spawn_pool >= 2 and W >= 12:
            max_war_spawns = min(W // 12, spawn_pool // 2)

        W_remaining = W - max_war_spawns * 12
        spawn_pool_after_war = spawn_pool - max_war_spawns * 2

        if spawn_pool_after_war >= 2 and W_remaining >= 10:
            max_farm_spawns = min(W_remaining // 10, spawn_pool_after_war // 2)

        # Assign groups
        #  - Base farming farmers
        for idx in range(base_farm_count):
            environment.assign_group(farmers[idx], "farm")

        #  - Spawn warriors (use next 2*max_war_spawns farmers)
        curr = base_farm_count
        for _ in range(max_war_spawns):
            if curr < F:
                environment.assign_group(farmers[curr], "spawn warrior")
                curr += 1
            if curr < F:
                environment.assign_group(farmers[curr], "spawn warrior")
                curr += 1

        #  - Spawn farmers (use next 2*max_farm_spawns farmers)
        for _ in range(max_farm_spawns):
            if curr < F:
                environment.assign_group(farmers[curr], "spawn farmer")
                curr += 1
            if curr < F:
                environment.assign_group(farmers[curr], "spawn farmer")
                curr += 1

        #  - Any remaining farmers go to farming
        while curr < F:
            environment.assign_group(farmers[curr], "farm")
            curr += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: stay in cave
                environment.assign_group(c, "cave")