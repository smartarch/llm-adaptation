from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # Get available wheat from the farm (robust access)
        wheat = 0
        try:
            wheat = getattr(environment.farm, 'wheat')
        except Exception:
            wheat = 0

        # Decide how many spawns (X for farmers, Y for warriors) we can support
        # Constraint: 10*X + 12*Y <= wheat, and 2*X + 2*Y <= len(farmers)
        max_X = min(len(farmers) // 2, wheat // 10 if wheat >= 0 else 0)

        best = None  # (total_spawns, X, Y)
        for X in range(max_X + 1):
            remaining_farmers = len(farmers) - 2 * X
            remaining_wheat = wheat - 10 * X
            if remaining_wheat < 0:
                continue
            Y = min(remaining_farmers // 2, remaining_wheat // 12)
            total_spawns = X + Y
            if best is None or total_spawns > best[0]:
                best = (total_spawns, X, Y)

        if best is None:
            X = 0
            Y = 0
        else:
            _, X, Y = best

        idx = 0
        # Assign 2*X farmers to spawn farmer group
        for _ in range(2 * X):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn farmer')
                idx += 1

        # Assign 2*Y farmers to spawn warrior group
        for _ in range(2 * Y):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], 'spawn warrior')
                idx += 1

        # Remaining farmers go to the regular farm group
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], 'farm')

        # All Warriors should go to the Cave (cave group) so they can attack
        for w in warriors:
            environment.assign_group(w, 'cave')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, 'attack')
            else:
                # Farmers in cave should head back to Village
                environment.assign_group(c, 'village')