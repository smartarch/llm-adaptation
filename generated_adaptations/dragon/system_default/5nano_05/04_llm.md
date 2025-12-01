Reasoning and adaptation plan

- Goal: Kill the Dragon as fast as possible. We want to maximize early DPS with Warriors while sustaining wheat production to enable spawning more villagers when wheat allows.
- Observations for improvement:
  - Warriors are the primary DPS. All Warriors should be in the Cave attacking the Dragon as soon as possible.
  - Farmers must stay in the Village to farm wheat and to spawn new villagers when resources allow.
  - Spawning rules require both villagers in a spawn group and sufficient wheat. Spawning more quickly requires balancing wheat income (farmers) with spawn group allocation.
- Strategy improvements:
  - Use a dynamic, step-aware spawning plan. In early steps, attempt to spawn up to one Warrior if we have enough farmers and wheat, to boost early DPS. In later steps, continue farming when wheat is low and spawn when wheat is sufficient.
  - Always keep all Warriors in the Cave to maximize immediate damage.
  - Allocate Farmers to: (a) spawn farmer groups to boost wheat production later, (b) spawn warrior groups to boost DPS, and (c) farm group to maximize wheat when spawning isn’t immediately viable.
  - Compute spawning based on available farmers and current wheat, ensuring we never allocate more villagers to spawn groups than we have.

What changes I will implement:
- In assign_in_village:
  - Classify villagers into Farmers and Warriors.
  - Keep all Warriors in the Cave.
  - For Farmers, compute a dynamic split:
    - Early steps (step < 15): try to spawn up to 1 Warrior if there are at least 2 farmers and 12 wheat.
    - Compute how many additional Farmer-spawns (needs 2 farmers and 10 wheat per spawn) can be afforded with remaining resources.
    - Allocate 2 farmers per Farmer-spawn to "spawn farmer", then 2 farmers per Warrior-spawn to "spawn warrior", and the rest to "farm".
  - In assign_in_cave:
    - Warriors go to "attack".
    - Farmers go to "village".
    - Fallbacks go to "village" as a safety.
- This approach aims to accelerate early damage while ensuring wheat production for sustainability, with a simple, interpretable rule set.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        num_farmers = len(farmers)
        num_warriors = len(warriors)

        # Wheat available in Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn plan
        spawns_warrior = 0
        spawns_farmer = 0

        # Early steps: try to spawn at most 1 Warrior if resources allow
        if step < 15 and num_farmers >= 2 and wheat >= 12:
            spawns_warrior = min(1, num_farmers // 2, wheat // 12)

        # After deciding Warrior spawns, allocate Farmer-spawns with remaining resources
        remaining_farmers = num_farmers - (spawns_warrior * 2)
        remaining_wheat = wheat - (spawns_warrior * 12)

        # Farmer-spawns require 2 farmers and 10 wheat each
        spawns_farmer = min(remaining_farmers // 2, remaining_wheat // 10)

        # Remaining farmers after spawns go to farming
        farm_villagers = remaining_farmers - (spawns_farmer * 2)

        # Assign Warriors to cave (they should attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Assign Farmers to groups
        # 1) Farmer-spawn group
        idx = 0
        for i in range(spawns_farmer * 2):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # 2) Warrior-spawn group
        for i in range(spawns_warrior * 2):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # 3) Farming group for the rest
        for i in range(farm_villagers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # Fallback: any leftover farmers (edge cases) -> farm
        remaining = num_farmers - idx
        for i in range(remaining):
            environment.assign_group(farmers[idx + i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack; Farmers should return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "village")
```