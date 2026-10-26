## Analysis of the previous run

- **The stall is caused by stale state.** `cave_warriors` is only updated in `assign_in_cave`. When the last Warrior dies, the Cave is empty, so `assign_in_cave` is never called again and the count stays at its last non-zero value.
- **The stale count keeps the farm reserve on.** The village logic believes Warriors are still alive, so it holds one Farmer on the farm and requires an extra Farmer for each spawn pair. With only one or two Farmers left, nothing attacks and nothing spawns, which matches the flat HP lines (19, 24, and 29 earlier).
- **Dragon HP at a stall never recovers.** Once the Cave is empty and the village is stuck, the game runs until the 30-step limit.

## Changes in this version

1. **Reset the cave count every village phase.** The village phase reads the last cave count once and then clears it. If the Cave was empty on the previous step, the stale value cannot persist.
2. **Reserve a farmer only when it is useful.** The farm reserve applies only when Warriors are actually alive and at least two Farmers are present. A lone Farmer is sent to attack instead of sitting idle.
3. **Never leave the Cave empty.** Any Farmer that is not spawning goes to the Cave when no Warriors are alive.
4. **Keep the proven attack structure.** Warriors go to the Cave, and every villager in the Cave attacks each step. Two Warrior pairs per step and a target of 10 Warriors are unchanged from the 11.3-step version.

This is a reasoned fix for a diagnosed bug, not a verified result. The simulation should confirm whether the stalls disappear.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 10       # total warriors (village + cave) to maintain
    MAX_WARRIOR_PAIRS = 2      # warrior spawn pairs per step
    MIN_VILLAGE_FARMERS = 1    # farmers kept on the farm while warriors are alive

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0   # warriors seen in the cave on the last cave phase
        self.cave_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Read the last observed cave count once, then clear it. The cave phase
        # is not called when the cave is empty, so a stale value must not persist.
        total_warriors = len(warriors) + self.cave_warriors
        self.cave_warriors = 0
        self.cave_farmers = 0

        available = list(farmers)
        budget = wheat

        # Keep a farm reserve only while warriors are alive and there is spare labour.
        reserve_needed = self.MIN_VILLAGE_FARMERS if total_warriors > 0 else 0

        # 2) Spawn warriors from village farmers, respecting the reserve.
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2 + reserve_needed
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1      # count the pending spawn
            warrior_pairs += 1

        # 3) Keep the reserve on the farm, but only if it is needed.
        reserve = min(reserve_needed, len(available))
        for f in available[:reserve]:
            environment.assign_group(f, "farm")

        # 4) All remaining farmers join the attack (1 damage each per step).
        for f in available[reserve:]:
            environment.assign_group(f, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        self.cave_warriors = len(warriors)
        self.cave_farmers = len(farmers)

        # Everyone in the cave attacks: retaliation is per step, not per attacker.
        for c in components:
            environment.assign_group(c, "attack")
```