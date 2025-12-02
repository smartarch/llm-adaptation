from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave (to head towards the Dragon)
        for c in warriors:
            environment.assign_group(c, "cave")

        F = len(farmers)
        if F == 0:
            # Nothing to do if no farmers exist
            return

        current_wheat = getattr(environment.farm, "wheat", 0)

        # 2) Enumerate possible farming/spawn plans to maximize Warrior spawns this turn
        # We will choose f (number of farmers that farm this turn) to maximize y (Warriors spawned)
        best_plan = None  # (f, y)
        best_y = -1
        best_f = -1

        for f in range(0, F + 1):
            total_wheat = current_wheat + f * 5  # wheat after farming f farmers this turn
            # Maximum Warriors we could spawn given f farmers and available wheat
            y = min((F - f) // 2, total_wheat // 12)
            if y > best_y:
                best_y = y
                best_f = f
                best_plan = (f, y)
            elif y == best_y and f > best_f:
                best_f = f
                best_plan = (f, y)

        if best_plan is None:
            best_plan = (F, 0)

        f, y = best_plan  # f = farmers farming this turn, y = number of Warrior spawns

        spawn_warrior_count = 2 * y
        farming_count = F - spawn_warrior_count
        spawn_farmer_count = 0  # This strategy does not spawn farmers this turn

        # Build the final groups
        spawn_warrior_villagers = farmers[:spawn_warrior_count]
        farming_villagers = farmers[spawn_warrior_count:]

        for c in spawn_warrior_villagers:
            environment.assign_group(c, "spawn warrior")

        for c in farming_villagers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: All Warriors go to Attack; Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")