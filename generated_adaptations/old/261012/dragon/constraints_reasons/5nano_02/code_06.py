from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to a single final group per component.
        Strategy for farmers:
          - Compute S (farmer-spawns) and W (warrior-spawns) to maximize total spawns.
          - Among equal total spawns, maximize W to ensure warrior spawning.
        Groups:
          - Warriors -> "cave"
          - Spawn groups and farming decisions assigned to Farmers:
              2*S farmers -> "spawn farmer"
              2*W farmers -> "spawn warrior"
              remaining farmers -> "farm"
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        N = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Enumerate all feasible (S, W) to maximize spawns, with tie-break on W
        best_S, best_W = 0, 0
        best_total = -1

        for S in range(0, N // 2 + 1):  # number of farmer-spawns
            max_W_by_farmers = (N - 2 * S) // 2
            for W in range(0, max_W_by_farmers + 1):
                if 10 * S + 12 * W <= wheat:
                    total = S + W
                    if total > best_total or (total == best_total and W > best_W):
                        best_total = total
                        best_S = S
                        best_W = W

        S = best_S
        W = best_W

        final_group = {}

        # Warriors: always move to cave in village phase
        for w in warriors:
            final_group[w] = "cave"

        idx = 0
        # First 2*S farmers to "spawn farmer"
        for i in range(2 * S):
            final_group[farmers[idx]] = "spawn farmer"
            idx += 1
        # Next 2*W farmers to "spawn warrior"
        for i in range(2 * W):
            final_group[farmers[idx]] = "spawn warrior"
            idx += 1
        # Remaining farmers to "farm"
        while idx < N:
            final_group[farmers[idx]] = "farm"
            idx += 1

        # Apply final groups, ensuring exactly one assignment per component
        for comp in components:
            grp = final_group.get(comp, "farm")
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, move Warriors to attack and Farmers back to village.
        """
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                environment.assign_group(comp, "village")