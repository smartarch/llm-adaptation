Reasoning and adaptation strategy

Task analysis:
- Goal: Kill the Dragon as fast as possible within 30 steps, with the constraint that the Dragon must be attacked at least once in the first 15 steps.
- Structure: Villagers live in the Village and can farm (farm group) or go to the Cave (cave group). There are two spawn mechanisms:
  - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- Farm wheat is the global resource (environment.farm.wheat). Farming a Farmer produces 5 wheat.
- Warriors deal more damage (3) than Farmers (1). Dragons retaliate when attacked.
- Dragon starts with 50 HP; win on kill; lose if no villagers remain or if 30 steps pass.

Strategy outline:
- Compliance with constraints:
  - All Warriors should eventually go to the Cave and attack: assign all Warriors to move to Cave in village phase, then to Attack in cave phase.
  All Farmers should stay in Village: Farmers never move to the Cave; in cave phase they should be moved back to Village.
  - Spawn mechanics: We should spawn new Farmers and Warriors to sustain pressure on the Dragon while maintaining Farmer presence in the Village to farm.
  - To spawn, assign some Farmers to spawn groups, constrained by wheat in the Farm. We will distribute Farmers between:
    - spawn farmer (needs 10 wheat per spawn, consumes 2 Farmers per spawn)
    - spawn warrior (needs 12 wheat per spawn, consumes 2 Farmers per spawn)
    - the rest stay in farming (farm)
  - We will aim to spawn as many total as possible given current wheat and available Farmers, prioritizing a mix that yields both more farmers (to continue farming and producing wheat) and Warriors (to attack). Warriors will be sent to Cave in the next village-to-cave cycle and then to Attack in the cave cycle.
- Step-by-step in code:
  - In assign_in_village:
    - Gather Farmers and Warriors currently in Village.
    - Compute how many spawn actions you can perform this step given the Wheat on the Farm:
      - spawns_farm = min(len(farmers) // 2, wheat // 10)
      - After reserving 2*spawns_farm Farmers for spawn_farm, compute spawns_war = min((len(farmers) - 2*spawns_farm) // 2, wheat // 12)
    - Assign the first 2*spawns_farm Farmers to group "spawn farmer".
    - Assign the next 2*spawns_war Farmers to group "spawn warrior".
    - The remaining Farmers stay in "farm".
    - Assign all Warriors to group "cave" (move to Cave to eventually Attack).
  - In assign_in_cave:
    - Move all Warriors to "attack" (they will attack the Dragon).
    - Move all Farmers to "village" (they should stay in Village).
- Rationale: This approach ensures:
  - Warriors begin moving to the Cave early (attack planning starts within first steps).
  - Farmers keep farming to build Wheat, enabling spawns for both Farmers and Warriors.
  - Spawn groups are used to create more villagers, both Farmers and Warriors, so the population can sustain a long-term push to kill the Dragon.
  - The spawn logic adheres to the exact mechanics described (two villagers in the spawn group plus required Wheat).

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay and farm
        - cave: go to the Cave (will be moved to attack in cave phase)
        - spawn farmer: for every two villagers assigned here and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers assigned here and 12 wheat, spawn a Warrior
        Strategy:
        - Move all Warriors to the Cave (to attack later).
        - For Farmers, allocate some to spawn farmers and spawn warriors based on available wheat.
        - Remaining farmers go to farming.
        - This keeps a balance between growing wheat (to enable spawns) and spawning new villagers.
        """
        # Separate current villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # If there are no farmers, we cannot spawn. We'll just move warriors to cave, and farmers (if any) to farm (none in this case).
        wheat = getattr(environment.farm, "wheat", 0)

        # Compute how many spawns we can perform this step given the wheat and available farmers
        spawns_farm = 0
        spawns_war = 0

        if len(farmers) >= 2:
            spawns_farm = min(len(farmers) // 2, wheat // 10)
            remaining_farmers_after_farm = len(farmers) - (spawns_farm * 2)
            # Re-evaluate wheat after reserving for farmer spawns
            wheat_after_farm = max(0, wheat - (spawns_farm * 10))
            spawns_war = 0
            if remaining_farmers_after_farm >= 2:
                spawns_war = min(remaining_farmers_after_farm // 2, wheat_after_farm // 12)

        # Assign groups for farmers
        # We will assign in order: first 2*spawns_farm to "spawn farmer",
        # next 2*spawns_war to "spawn warrior",
        # the rest to "farm"
        for idx, f in enumerate(farmers):
            if idx < spawns_farm * 2:
                environment.assign_group(f, "spawn farmer")
            elif idx < (spawns_farm * 2) + (spawns_war * 2):
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Assign all Warriors to cave (to move to Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Note: If there are any villagers not covered (unexpected cases), default to staying in farm
        # (This ensures every component is assigned to one of the valid groups.)
        # (All villagers should have been assigned by now.)
        # Safety check (optional): ensure every component is assigned at least to something
        # (not strictly necessary; engine will ignore duplicates.)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        Strategy:
        - All Warriors should attack the Dragon, so assign all Warriors to "attack".
        - All Farmers should return to the Village, so assign them to "village".
        - This keeps farmers in the Village and ensures warriors are ready to attack.
        """
        for c in components:
            role = getattr(c, "role", "")
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback: keep in cave if unknown role
                environment.assign_group(c, "cave")
```