Reasoning and updated adaptation strategy

Goal recap:
- Warriors must go to the Cave and attack the Dragon.
- Farmers stay in the Village to farm and/or spawn new villagers.
- Spawning uses 2 villagers + a Wheat cost (10 for Farmer, 12 for Warrior).
- We want to minimize turns to kill the Dragon (50 HP) while managing risk from the Dragon’s retaliation (it can hit villagers in the Cave).

What was suboptimal in the previous approach:
- It aggressively allocated farmers to spawn Farmer and Warrior groups purely based on current wheat, with no explicit step-based pacing. This can waste wheat early or underutilize farming when needed most, potentially delaying the build-up of a DPS force in cave.
- It didn’t explicitly gate spawning by game step, which can cause overspending wheat on spawns too early and under-building DPS later.

Improved adaptation strategy:
- Step-aware spawning: implement a simple, deterministic budget per step to control how aggressively we spawn new villagers.
  - Steps 0-2: focus on farming to accumulate wheat. Do not spawn.
  - Steps 3-5: start small spawns (at most 1 new villager per step; i.e., up to 1 new Farmer or Warrior per step, depending on available wheat and farmers).
  - Steps 6 and beyond: allow up to 2 spawns per step to accelerate population growth and DPS.
- Spawn prioritization:
  - First allocate as many spawns as allowed by the budget to farmers (spawn farmer) since farmers directly increase wheat production, enabling future spawns.
  - Use remaining budget to spawn warriors (spawn warrior) if enough farmers exist and wheat is available.
  - All Warriors go to the Cave (attack); Farmers stay in Village to farm or spawn.
- This pacing ensures early wheat accumulation while gradually building a larger, more capable army in the Cave, increasing the likelihood of defeating the Dragon within 30 steps.

Code (Python) implementing the strategy

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Step-based spawn budgeting
        if step < 3:
            max_spawns = 0
        elif step < 6:
            max_spawns = 1
        else:
            max_spawns = 2

        # Compute how many spawns we can support this step
        # Each spawn requires 2 farmers and a Wheat cost (10 for Farmer, 12 for Warrior)
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_farmers = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_farmers // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        # Assign farmers to groups
        spawn_farmer_assignees = farmers[:n_sf]
        spawn_warrior_assignees = farmers[n_sf:n_sf + n_sw]
        farm_assignees = farmers[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are no farmers, Warriors have already been sent to cave above.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should move back to Village to farm or spawn
                environment.assign_group(c, "village")
```