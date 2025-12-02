from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # All Warriors go to the cave (attack the Dragon)
        for c in warriors:
            environment.assign_group(c, 'cave')

        # Wheat available for spawning
        W = getattr(environment, 'farm').wheat if hasattr(environment, 'farm') else 0
        F = len(farmers)

        # Optimize number of spawns a (spawn farmer) and b (spawn warrior)
        best_S = -1
        best_a = 0
        best_b = 0

        max_a = min(F // 2, W // 10)  # maximum possible farmer spawns given farmers and wheat
        for a in range(0, max_a + 1):
            remaining_farmers = F - 2 * a
            if remaining_farmers < 0:
                continue
            max_b_by_farm = remaining_farmers // 2
            rem_wheat = W - 10 * a
            if rem_wheat < 0:
                continue
            max_b_by_wheat = rem_wheat // 12
            b = min(max_b_by_farm, max_b_by_wheat)
            S = a + b
            if S > best_S:
                best_S = S
                best_a = a
                best_b = b

        a = best_a
        b = best_b

        idx = 0
        # Assign first 2*a farmers to spawn farmer
        for i in range(min(2 * a, len(farmers))):
            environment.assign_group(farmers[idx], 'spawn farmer')
            idx += 1

        # Assign next 2*b farmers to spawn warrior
        for i in range(min(2 * b, len(farmers) - idx)):
            environment.assign_group(farmers[idx], 'spawn warrior')
            idx += 1

        # Remaining farmers go to farming
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors stay in cave and attack; Farmers go to village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:  # Farmer
                environment.assign_group(c, 'village')