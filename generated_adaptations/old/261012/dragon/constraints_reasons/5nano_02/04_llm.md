Reasoning and strategy update

Issue identified:
- The previous implementation assigned each farmer to multiple groups within a single assign_in_village call (e.g., both "farm" and "spawn farmer"), triggering the test failure about repeated assignments. The tests require exactly one group per component per call.
- To fix this, we must decide a single final group for every village component in assign_in_village and then assign each component to that final group exactly once.

Strategy:
- Do not perform incremental re-assignments. Instead, compute a single final_group for each villager in the village.
- Warriors: always assign to the "cave" group in the village phase (they will transition to "attack" in the cave phase).
- Farmers: stay in the village but participate in spawning when possible.
  - We will maximize spawns given constraints:
    - Let N be the number of farmers in the village, wheat be environment.farm.wheat.
    - Compute spawns for farmers (S) and spawns for warriors (W) using the requirement that for each spawn there must be 2 villagers assigned to the spawn group and 10 wheat (for farmers) or 12 wheat (for warriors).
    - We aim to maximize total spawns with the available farmers and wheat:
      - S = min(N // 2, wheat // 10)
      - After allocating 2*S farmers to "spawn farmer", remaining farmers = N - 2*S
      - Remaining wheat = wheat - 10*S
      - W = min( remaining_farmers // 2, remaining_wheat // 12 )
    - Then assign:
      - The first 2*S farmers to "spawn farmer"
      - The next 2*W farmers to "spawn warrior"
      - All remaining farmers to "farm"
- All assignments are computed first, then applied in a single pass to ensure exactly one assignment per component.

This satisfies:
- All Warriors go to the Cave (in village phase) and will be moved to attack in cave phase.
- All Farmers stay in Village (via "farm", "spawn farmer", or "spawn warrior" groups).
- Spawn groups are used aggressively when wheat permits, creating new villagers and ensuring the "few new farmers and a few new warriors" constraint is met.
- No repeated assignments: each component gets exactly one final group per assign_in_village call.

Code (Python) implementing the updated strategy

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to a single final group per component:
        - Warriors -> cave
        - Farmers -> either farm, spawn farmer, or spawn warrior
        Spawning is maximized given current wheat to increase population.
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Prepare final group mapping (one group per component)
        final_group = {}

        # 1) Warriors always go to cave now
        for w in warriors:
            final_group[w] = "cave"

        # 2) Farmers decide whether to farm or spawn
        N = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Initialize all farmers to spawn logic
        S = min(N // 2, wheat // 10)  # number of farmer-spawns
        wheat_after_farm_spawns = wheat - 10 * S
        remaining_farmers_after_f = N - 2 * S
        W = min(remaining_farmers_after_f // 2, wheat_after_farm_spawns // 12)  # number of warrior-spawns

        # Pick farmers for spawns
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
            grp = final_group.get(comp, None)
            if grp is None:
                # Fallback: keep in village farming
                grp = "farm"
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, move Warriors to attack and Farmers back to village.
        """
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            elif role == "Farmer":
                environment.assign_group(comp, "village")
            else:
                environment.assign_group(comp, "village")
```