Reasoning for improvement

- Problem with the previous approach: While early aggression is good, spawning decisions were not always maximizing early DPS. If we delay Warrior spawns or underutilize wheat, the Dragon can survive longer and cause more casualties in the Cave. The key to a faster win is to push DPS up as early as possible, but without depleting wheat and farmers to the point where we can’t sustain spawns later.

- Updated strategy (greedy early DPS):
  - Always move all Warriors to the Cave so they start dealing damage immediately.
  - In the Village, prioritize spawns to boost early DPS:
    - First, spawn Warriors as early as possible (requires 2 Farmers and 12 wheat per Warrior spawn). More Warriors in the cave means higher DPS quickly.
    - Then, if wheat and Farmers allow, spawn Farmers (requires 2 Farmers and 10 wheat per Farmer spawn) to grow wheat production for future spawns.
  - This greedy ordering aims to maximize DPS in the shortest time, increasing the chances to kill the Dragon within the 30-step window while still enabling ongoing population growth for future DPS.
  - Farmers stay in the Village unless they’re donors for spawns in the Village step; Farmers are not allocated to the Cave, so the Dragon’s counterattacks affect fewer villagers.

What changes are made
- In assign_in_village:
  - Move all Warriors to the Cave immediately (as required).
  - Compute the maximum possible Warrior spawns given current Farmers and wheat, then perform those spawns.
  - With remaining Farmers and wheat, compute and perform as many Farmer spawns as possible.
  - The rest of Farmers stay in the Village (group "farm").
- In assign_in_cave:
  - Keep Warriors in attack mode ("attack" group).
  - Move Farmers back to the Village ("village" group) to avoid casualties and keep Wheat production going.

Python code (one block)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Identify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave for early DPS
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Greedy spawning: prefer Warrior spawns first to boost early DPS
        wheat = getattr(environment.farm, "wheat", 0)
        n_farmers = len(farmers)

        max_war_spawns = 0
        if n_farmers >= 2 and wheat >= 12:
            max_war_spawns = min(n_farmers // 2, wheat // 12)

        remaining_farmers = n_farmers - 2 * max_war_spawns
        wheat_after_war = wheat - 12 * max_war_spawns

        max_farm_spawns = 0
        if remaining_farmers >= 2 and wheat_after_war >= 10:
            max_farm_spawns = min(remaining_farmers // 2, wheat_after_war // 10)

        # 3) Assign groups for Farmers
        idx = 0
        # First the Warrior spawns
        for i in range(max_war_spawns * 2):
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")
            idx += 1
        # Then the Farmer spawns
        for i in range(max_farm_spawns * 2):
            c = farmers[idx]
            environment.assign_group(c, "spawn farmer")
            idx += 1
        # Rest stay farming in Village
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: attack with Warriors; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```