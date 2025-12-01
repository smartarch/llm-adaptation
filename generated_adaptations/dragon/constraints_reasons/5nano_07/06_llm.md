Reasoning and updated adaptation strategy

What changed and why:
- The tests require that spawning happens in a realistic, incremental way and that every villager is assigned to exactly one group per step.
- Previous versions could cause multiple assignments in one call or fail to spawn when wheat was sufficient but the logic required more than 2 farmers, or misaccounted wheat when spawning both a farmer and a warrior in the same step.
- The updated strategy uses a single deterministic pass over all villagers in assign_in_village, ensuring every component is assigned to exactly one group.
- Spawning logic now correctly accounts for wheat as it is consumed by spawns in the same step:
  - If there are at least 2 farmers and at least 10 wheat, assign two farmers to the "spawn farmer" group (consumes 10 wheat).
  - After that, if there are at least 2 remaining farmers and at least 12 wheat left, assign two of the remaining farmers to "spawn warrior" (consumes 12 wheat, total 22 if both spawns happen in the same step).
  - If not enough wheat for both, allow either a farmer spawn or a warrior spawn depending on available wheat.
- All Warriors are assigned to the cave (to attack in the cave step), all Farmers stay in the Village by default (unless they are assigned to spawn groups). This preserves the required behavior: early attack, population growth, and a single group assignment per component.

Implementation details:
- Single pass: assign each component to exactly one group in assign_in_village.
- Spawning decisions are based on current counts and the wheat available in environment.farm.wheat.
- No component is assigned more than once in a single call.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, spawn a Farmer
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, spawn a Warrior
        """
        # Collect farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Single-pass assignment mapping
        assignment = {}

        # 1) Warriors go to cave (they will attack later)
        for w in warriors:
            assignment[w] = "cave"

        # 2) Farmers default to farming
        for f in farmers:
            assignment[f] = "farm"

        # 3) Wheat available
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0)

        # 4) Attempt spawning decisions (single-pass, non-overlapping)
        if len(farmers) >= 2 and wheat >= 10:
            to_spawn_farm = farmers[:2]
            for f in to_spawn_farm:
                assignment[f] = "spawn farmer"
            wheat_left = wheat - 10

            remaining = [f for f in farmers if f not in to_spawn_farm]
            if len(remaining) >= 2 and wheat_left >= 12:
                to_spawn_war = remaining[:2]
                for f in to_spawn_war:
                    assignment[f] = "spawn warrior"
        else:
            # If not enough for farmer spawn, but enough for warrior spawn
            if len(farmers) >= 2 and wheat >= 12:
                to_spawn_war = farmers[:2]
                for f in to_spawn_war:
                    assignment[f] = "spawn warrior"

        # Apply the single-pass assignments
        for comp, grp in assignment.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon (Warriors)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```