import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        W = int(getattr(environment.farm, "wheat", 0))

        # Reserve a baseline of farmers to keep farming
        min_farmers_to_remain = 2

        # 2) Spawn Warriors first: need 2 farmers and 12 wheat per spawn
        max_warrior_spawns = 0
        if F > min_farmers_to_remain and W >= 12:
            max_warrior_spawns = min((F - min_farmers_to_remain) // 2, W // 12)
        s_fw = 2 * max_warrior_spawns  # number of farmers to assign to "spawn warrior"

        # Wheat and farmers left after Warrior spawns
        rem_f = F - s_fw
        rem_w = W - 12 * max_warrior_spawns

        # 3) Spawn Farmers next: need 2 farmers and 10 wheat per spawn
        max_farmer_spawns = 0
        if rem_f >= 2 and rem_w >= 10:
            max_farmer_spawns = min(rem_f // 2, rem_w // 10)
        s_ff = 2 * max_farmer_spawns  # number of farmers to assign to "spawn farmer"

        # 4) Assign farmers to their respective groups
        idx = 0
        # First, assign to spawn warrior (2 per spawn)
        for _ in range(s_fw):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        # Next, assign to spawn farmer (2 per spawn)
        for _ in range(s_ff):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        # Remaining farmers stay in farming
        for j in range(idx, F):
            environment.assign_group(farmers[j], "farm")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors attack; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")

        return