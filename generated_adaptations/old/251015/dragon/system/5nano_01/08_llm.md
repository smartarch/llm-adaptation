Reasoning and improved adaptation strategy:
- Goal and constraints: Keep Warriors in the Cave to maximize DPS early, while Farmers stay in the Village to farm and spawn new villagers. Spawns consume wheat and two villagers. We want to accelerate growth without sacrificing too much short-term wheat production.
- What changed from prior approach:
  - Introduce a dynamic, step-aware spawning policy instead of a fixed cap. Aggressiveness is higher in the very early game and tapers off as the game progresses to preserve farming output.
  - Spawning policy in the Village:
    - Always move all Warriors to the Cave.
    - Determine how many Farmer spawns to attempt based on current step and wheat:
      - Early game (step <= 5): allow up to 3 Farmer spawns (i.e., up to 6 Farmers used) if wheat permits.
      - Mid game (step 6-10): allow up to 2 Farmer spawns.
      - Late game (step > 10): allow up to 1 Farmer spawn.
    - After Farmer spawns, consider Warrior spawns if there are at least 2 remaining Farmers and at least 12 wheat, but cap Warrior spawns to 2 per step to avoid starving farming.
    - Remaining Farmers go to the "farm" group to maximize ongoing wheat production.
  - Cave behavior remains: Warriors Attack; Farmers Retreat to Village.
- This approach aims to reduce the total number of turns to kill the Dragon by boosting early population growth without compromising short-term wheat income too much, while still delivering DPS gains mid-game.

Python code (class SmartAdaptation implementing the improved strategy):

```py
import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Warriors -> cave (to go attack)
        - Farmers -> spawn farmers in a dynamic batch (based on step and wheat),
                     then possibly spawn warriors if wheat allows,
                     finally remaining farmers go to farming.
        """
        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # 1) Send all Warriors to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Wheat info (current wheat in farm)
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0)

        fcount = len(farmers)

        # 3) Determine spawn farmer actions (dynamic batching)
        if step <= 5:
            cap = 3
        elif step <= 10:
            cap = 2
        else:
            cap = 1

        spawns_farmers = 0
        if fcount >= 2 and wheat >= 10:
            max_farm_spawns = min(fcount // 2, wheat // 10)
            spawns_farmers = min(max_farm_spawns, cap)

        # Assign 2*spawns_farmers farmers to "spawn farmer"
        idx = 0
        for _ in range(spawns_farmers * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        remaining_farmers = farmers[idx:]  # farmers not used for spawn farmers

        # Wheat after farm spawns
        wheat_after_farm_spawns = wheat - spawns_farmers * 10

        # 4) Determine possible spawns for warriors using remaining farmers and wheat
        spawns_warriors = 0
        if len(remaining_farmers) >= 2 and wheat_after_farm_spawns >= 12:
            spawns_warriors = min(len(remaining_farmers) // 2,
                                  wheat_after_farm_spawns // 12,
                                  2)

        # Assign 2*spawns_warriors farmers to "spawn warrior"
        for i in range(spawns_warriors * 2):
            if i < len(remaining_farmers):
                environment.assign_group(remaining_farmers[i], "spawn warrior")

        # Remaining farmers after both spawn operations go to farming
        start_idx_for_farm = spawns_farmers * 2 + spawns_warriors * 2
        for j in range(start_idx_for_farm, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # Note: This ensures every Farmer is assigned to exactly one group.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors -> attack (attack the Dragon)
        - Farmers -> village (go back to the Village)
        """
        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```