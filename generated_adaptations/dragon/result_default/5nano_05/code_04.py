from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available for spawning (best effort to read current wheat)
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            try:
                wheat = int(environment.farm.wheat)
            except Exception:
                wheat = 0

        n_farmers = len(farmers)
        assigned_to_spawn_farm = 0
        assigned_to_spawn_warrior = 0

        i = 0
        # Phase 1: Spawn as many farmers as possible (2 farmers + 10 wheat)
        while i + 1 < n_farmers and wheat >= 10:
            c1 = farmers[i]
            c2 = farmers[i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            assigned_to_spawn_farm += 2
            i += 2
            wheat -= 10

        # Phase 2: With remaining farmers, spawn warriors (2 farmers + 12 wheat)
        while i + 1 < n_farmers and wheat >= 12:
            c1 = farmers[i]
            c2 = farmers[i + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            assigned_to_spawn_warrior += 2
            i += 2
            wheat -= 12

        # Phase 3: Remaining farmers stay in farming
        for idx in range(n_farmers):
            c = farmers[idx]
            if idx < i:  # already assigned to a spawn group
                continue
            environment.assign_group(c, "farm")

        # All Warriors go to the Cave (to attack Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")