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
        - Among Farmers in the Village, spawn as many new Farmers and Warriors as allowed by the available wheat.
        - The rest of Farmers stay to farm.
        """
        # Gather villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the Cave (attack group)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Determine how many spawns we can perform this turn using current wheat
        F = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Compute spawn farmer count (2 farmers per spawn, costs 10 wheat per spawn)
        spawn_f_count = 0
        if F >= 2 and wheat >= 10:
            spawn_f_count = min(F // 2, wheat // 10)

        # Remaining farmers after allocating for spawn farmers
        remaining_after_f = F - (2 * spawn_f_count)

        # Compute spawn warrior count (2 villagers per spawn, costs 12 wheat per spawn)
        spawn_w_count = 0
        if remaining_after_f >= 2 and wheat - (spawn_f_count * 10) >= 12:
            spawn_w_count = min(remaining_after_f // 2, (wheat - (spawn_f_count * 10)) // 12)

        # 3) Assign groups
        idx = 0

        # Assign to spawn farmer group
        for _ in range(2 * spawn_f_count):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Assign to spawn warrior group
        for _ in range(2 * spawn_w_count):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers go to farming
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