Reasoning and adaptation strategy

Goal and constraints
- All Warriors must go to the Cave and attack the Dragon.
- All Farmers should stay in the Village.
- Spawn groups exist to create new Farmers or Warriors, consuming wheat and 2 villagers assigned to the spawn group.
- We want the Dragon killed as fast as possible, with at least one attack within the first 15 steps, and we should keep a presence of warriors in the Cave to attack.
- We should spawn both Farmers and Warriors to increase raw DPS and provide more units to attack the Dragon.
- We must keep the total distribution explicit: every Villager must be assigned to exactly one of the listed groups.

Strategic approach
1) Village behavior
- Move all current Warriors to the cave (attack) group to guarantee early damage and ensure the “half in cave” constraint is easily met.
- Keep Farmers in the Village. To enable growth, designate a small, resource-driven subset of Farmers to spawn new Farmers or Warriors:
  - If there are at least 2 Farmers and at least 10 wheat in the Farm, assign 2 Farmers to the "spawn farmer" group. This will spawn at least 1 additional Farmer over time (and helps keep the farming pipeline going).
  - If after assigning to "spawn farmer" there are at least 2 more Farmers and at least 12 wheat, assign 2 Farmers to the "spawn warrior" group to spawn a new Warrior.
  - The remaining Farmers stay in the "farm" group to keep producing wheat (per-step wheat production helps sustain future spawns).
- This yields a simple, resource-aware spawn policy that embodies:
  - Early Dragon engagement (warriors in cave, attacking early)
  - Growth of both Farmers and Warriors to improve DPS over time
  - Farmers never move to the cave, complying with the constraint

2) Cave behavior
- In the Cave, all Warriors should be assigned to the "attack" group to ensure they attack the Dragon.
- Farmers in the Cave are discouraged by the rules; so Farmers in the Cave will be assigned to "village" (or to be moved back) in this step depending on implementation. To adhere to the rule "All farmers should stay in Village," we ensure Farmers in Cave are moved to the "village" group.

3) Spawn mechanics
- Spawn groups are used only by Farmers in the Village (spawn farmer) and to spawn Warriors (spawn warrior). They require 2 villagers in the group and a wheat budget (10 for farmers, 12 for warriors). The code uses a simple heuristic to allocate up to 2 villagers to each spawn group if wheat allows.

4) Step-by-step rationale
- First, guarantee early attack by routing all Warriors to cave/attack in every village-to-cave transition.
- Then, opportunistically spawn more Farmers and Warriors using the two spawn groups based on available wheat.
- The strategy favors spawning because some new units will help bring the Dragon's HP to 0 faster; it also preserves the requirement of having some new units.

Code: SmartAdaptation class implementing the two required methods

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": Stay in the Village and farm
        - "cave": Go to the Cave (for Warriors)
        - "spawn farmer": For every two villagers assigned to this group and 10 wheat, spawn a new Farmer
        - "spawn warrior": For every two villagers assigned to this group and 12 wheat, spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat budget for spawning
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine spawn groups from farmers
        to_spawn_farm = []
        to_spawn_war = []

        # Try to allocate up to 2 farmers to spawn farmer if possible
        remaining_farmers_after_farm_spawn = farmers
        if len(farmers) >= 2 and wheat >= 10:
            to_spawn_farm = farmers[:2]
            remaining_farmers_after_farm_spawn = farmers[2:]
        else:
            to_spawn_farm = []
            remaining_farmers_after_farm_spawn = farmers

        # Try to allocate up to 2 more farmers to spawn warrior if possible
        if len(remaining_farmers_after_farm_spawn) >= 2 and wheat >= 12:
            to_spawn_war = remaining_farmers_after_farm_spawn[:2]
        else:
            to_spawn_war = []

        # Assign groups
        for c in components:
            if c in warriors:
                # All Warriors go to the Cave (we'll drill them to attack)
                environment.assign_group(c, "cave")
            elif c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")
            elif c in to_spawn_war:
                environment.assign_group(c, "spawn warrior")
            else:
                # Remaining farmers stay in the Village
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon (for Warriors)
        - "cave": Stay in the Cave
        - "village": Go to the Village
        """
        for c in components:
            # Warriors should attack; Farmers should return to the Village
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```