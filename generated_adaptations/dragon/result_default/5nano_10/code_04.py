from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Strategy:
        # - Keep at least 2 farmers for farming (if possible)
        # - Spawn as many Warriors as possible with remaining farmers and wheat
        # - Then spawn Farmers with what's left

        # Compute Warrior spawns: each pair uses 2 farmers and 12 wheat
        if F >= 3:
            # Reserve at least 2 farmers for farming, use the rest for Warrior spawns
            max_warrior_pairs_by_farmers = (F - 2) // 2
            max_warrior_pairs_by_wheat = W // 12
            warrior_pairs = min(max_warrior_pairs_by_farmers, max_warrior_pairs_by_wheat)
        else:
            warrior_pairs = 0

        spawn_warrior_count = 2 * warrior_pairs

        # Remaining farmers after Warrior spawns
        remaining_farmers_after_warrior = F - spawn_warrior_count

        # Compute Farmer spawns: each pair uses 2 farmers and 10 wheat
        if remaining_farmers_after_warrior >= 2:
            max_farm_pairs_by_farmers = remaining_farmers_after_warrior // 2
            max_farm_pairs_by_wheat = W // 10
            farm_pairs = min(max_farm_pairs_by_farmers, max_farm_pairs_by_wheat)
        else:
            farm_pairs = 0

        spawn_farm_count = 2 * farm_pairs

        # Assign groups for farmers
        idx = 0
        for f in farmers:
            if idx < spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            elif idx < spawn_warrior_count + spawn_farm_count:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")
            idx += 1

        # All warriors should go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, have Warriors attack; Farmers return to village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: stay in cave for safety
                environment.assign_group(c, "cave")