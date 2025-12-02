Strategy reasoning and description

Goal mapping:
- All Warriors should eventually go to the Cave and attack the Dragon.
- All Farmers should stay in the Village (but they can be used to spawn new villagers).
- Spawn groups allow creating new Farmers or Warriors by consuming wheat and using two villagers assigned to the respective spawn group.
- We want to attack early (at least once within the first 15 steps) and keep enough warriors in the Cave to maximize damage.

Strategy outline:
1) In the Village:
   - Default behavior: keep Farmers in the Village to farm wheat; move all Warriors to the Cave (via the Cave group) so they can prepare to attack.
   - Use spawning to increase reinforcements:
     - Use two Farmers as spawners to spawn one new Farmer if there is at least 10 wheat.
     - Use two Farmers as spawners to spawn one new Warrior if there is at least 12 wheat.
     - If enough farmers and wheat exist (roughly 4 farmers and at least 22 wheat), spawn a mix: 2 Farmers spawn Farmers and 2 Farmers spawn Warriors in the same step.
   - This approach ensures:
     - We generate new Farmers to help gather more wheat and sustain the farming loop.
     - We generate new Warriors to bolster the attacking force.
     - Warriors are kept in the Cave (soon they attack).
   - The strategy guarantees at least some attack by moving Warriors to the Cave early.

2) In the Cave:
   - All Warriors in the Cave should be assigned to the Attack group to actively damage the Dragon.
   - All Farmers in the Cave should be moved back to the Village (to stay faithful to the requirement that Farmers stay in Village).

3) Constraints awareness:
   - The environment’s wheat is consumed by spawn events (10 wheat for a Farmer spawn, 12 wheat for a Warrior spawn) and two villagers are required per spawn event.
   - The implementation uses a simple per-step decision (no cross-step memory) and relies on current state (counts of Farmers/Warriors and wheat). This is sufficient for a robust, deterministic adaptation without external state.

Code implementation (Python)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (to join warriors to attack)
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a new Farmer
        - spawn warrior: for every two villagers assigned here and 12 wheat, spawn a new Warrior
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Decide on spawn plans using simple per-step rules (no cross-step memory)
        spawn_farmers = []
        spawn_warriors = []

        # Try to spawn an optimal mix if resources allow
        # Case A: enough farmers to spawn both a farmer and a warrior this step
        if len(farmers) >= 4 and environment.farm.wheat >= 22:
            spawn_farmers = farmers[:2]    # first two as spawn farmer
            spawn_warriors = farmers[2:4]  # next two as spawn warrior
        # Case B: spawn only a warrior (needs 2 farmers and 12 wheat)
        elif len(farmers) >= 2 and environment.farm.wheat >= 12:
            spawn_warriors = farmers[:2]
        # Case C: spawn only a farmer (needs 2 farmers and 10 wheat)
        elif len(farmers) >= 2 and environment.farm.wheat >= 10:
            spawn_farmers = farmers[:2]
        # Fallback: no spawns this step

        # Build a map for quick lookup
        spawn_map = {}
        for c in spawn_farmers:
            spawn_map[id(c)] = "spawn farmer"
        for c in spawn_warriors:
            spawn_map[id(c)] = "spawn warrior"

        # Assign groups for each component
        for c in components:
            cid = id(c)
            if cid in spawn_map:
                environment.assign_group(c, spawn_map[cid])
            elif getattr(c, "role", None) == "Farmer":
                # Farmers stay in Village
                environment.assign_group(c, "farm")
            elif getattr(c, "role", None) == "Warrior":
                # Warriors go to Cave
                environment.assign_group(c, "cave")
            else:
                # Default fallback
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # All warriors in cave should attack
                environment.assign_group(c, "attack")
            elif getattr(c, "role", None) == "Farmer":
                # Farmers should go back to Village
                environment.assign_group(c, "village")
            else:
                # Unknown role; keep them in cave
                environment.assign_group(c, "cave")
```