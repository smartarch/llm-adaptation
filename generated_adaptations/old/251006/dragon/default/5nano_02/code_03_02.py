from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        Strategy:
        - Move all Warriors to the Cave (attack group).
        - Among Farmers in the Village, spawn as many new Warriors as possible given wheat.
        - Then spawn Farmers with any remaining wheat.
        - Remaining Farmers stay to farm.
        """
        # Gather villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the Cave (attack group)
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # 2) Determine spawns with a priority for Warriors (better DPS early)
        spawn_w_count = 0
        if F >= 2 and wheat >= 12:
            # Max number of Warrior spawns we can afford this turn
            spawn_w_count = min(F // 2, wheat // 12)

        wheat_after_w = wheat - (spawn_w_count * 12)
        farmers_after_w = F - (spawn_w_count * 2)

        spawn_f_count = 0
        if farmers_after_w >= 2 and wheat_after_w >= 10:
            spawn_f_count = min(farmers_after_w // 2, wheat_after_w // 10)

        idx = 0

        # 3) Assign to spawn warrior group (2 villagers per spawn)
        for _ in range(2 * spawn_w_count):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # 4) Assign to spawn farmer group (2 villagers per spawn)
        for _ in range(2 * spawn_f_count):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # 5) Remaining farmers go to farming
        for j in range(idx, F):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        Strategy: All Warriors should attack; Farmers should go to the Village.
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")