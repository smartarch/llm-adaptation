from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors should go to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village and are allocated to farming or spawning groups
        n_farmers = len(farmers)

        # Current wheat available for spawning (environment.farm.wheat)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # We want to maximize spawns: for sf spawns of Farmer and sw spawns of Warrior
        # Constraints:
        #  - 2*sf + 2*sw <= n_farmers
        #  - 10*sf + 12*sw <= wheat
        # We search all feasible (sf, sw) pairs and pick the one with maximum total spawns (sf+sw),
        # breaking ties arbitrarily (preferring more spawns).
        max_sf = min(n_farmers // 2, wheat // 10) if n_farmers >= 2 else 0
        best_sf, best_sw = 0, 0
        best_score = -1

        for sf in range(0, max_sf + 1):
            remaining_farmers = n_farmers - 2 * sf
            remaining_wheat = wheat - 10 * sf
            if remaining_wheat < 0:
                continue
            max_sw = min(remaining_farmers // 2, remaining_wheat // 12) if remaining_farmers >= 2 else 0
            if max_sw < 0:
                continue
            # We want to maximize spawns count
            sw = max_sw
            score = sf + sw
            if score > best_score:
                best_score = score
                best_sf, best_sw = sf, sw

        # Assign farmers to the spawn groups first, then remaining to farming
        idx = 0
        # To ensure deterministic behavior, keep an ordered list
        farmers_list = farmers[:]

        # Spawn farmer: 2 villagers per spawn
        for _ in range(2 * best_sf):
            if idx < len(farmers_list):
                environment.assign_group(farmers_list[idx], "spawn farmer")
                idx += 1

        # Spawn warrior: 2 villagers per spawn
        for _ in range(2 * best_sw):
            if idx < len(farmers_list):
                environment.assign_group(farmers_list[idx], "spawn warrior")
                idx += 1

        # Remaining farmers stay in farming group (in Village)
        while idx < len(farmers_list):
            environment.assign_group(farmers_list[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")