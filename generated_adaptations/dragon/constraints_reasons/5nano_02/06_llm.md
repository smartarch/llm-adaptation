Reasoning and strategy update

Issue addressed:
- The previous approach could yield zero warrior spawns in some scenarios, failing the functional constraint that requires spawning at least a few new warriors. Additionally, tests require a single final group per component in assign_in_village (no multiple assignments per call). We need a deterministic single-pass decision that both:
  - Ensures warriors spawn when possible, and
  - Maximizes the total number of spawns, preferring warrior spawns when counts tie.

Updated strategy:
- In assign_in_village, compute a single final group for every villager (no repeated assignments per call).
- For farmers, determine how many should be assigned to spawn farmer, spawn warrior, or farm by solving a small integer optimization:
  - Let N be the number of farmers in the village.
  - Let wheat be environment.farm.wheat.
  - We choose non-negative integers S and W (numbers of farmer-spawns and warrior-spawns) such that:
    - 2*(S + W) <= N (enough farmers to support spawns)
    - 10*S + 12*W <= wheat (wheat constraint)
  - We maximize total spawns (S + W). If multiple (S,W) yield the same total spawns, we prefer the one with more warrior spawns (W) to satisfy the "spawn a few new warriors" constraint.
- Apply grouping:
  - Warriors go to cave (group "cave" now; they will be moved to "attack" in assign_in_cave).
  - Farmers: the first 2*S go to "spawn farmer", the next 2*W go to "spawn warrior", the remainder go to "farm".
- All Warriors in the cave will later go to "attack" in assign_in_cave, satisfying the requirement that all warriors eventually attack.

Code (Python) implementing the updated strategy

```py
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
```