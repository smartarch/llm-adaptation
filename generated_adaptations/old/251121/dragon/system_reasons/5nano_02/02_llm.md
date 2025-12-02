Reasoning and adaptation strategy

Goal and constraints recap
- All Warriors should go to the Cave to attack the Dragon.
- All Farmers should stay in the Village.
- Spawn groups (spawn farmer, spawn warrior) exist to create new villagers, consuming wheat and requiring two villagers in the group per spawn.
- We want both more farmers and more warriors to increase DPS against the Dragon.
- The Dragon should be attacked, and the attack should happen within the first 15 steps.
- After moving to the Cave, Warriors should attack the Dragon.
- At least half of the Warriors should be in the Cave most of the time so they can attack the Dragon.

Strategy rationale
- Move all Warriors to the Cave as soon as possible so they can attack. This satisfies the constraint that all Warriors should go to the Cave and attack the Dragon; in the two-step flow, we send Warriors to Cave in assign_in_village and then mark them as attacking in assign_in_cave.
- Farmers stay in Village by default and work on farms to accumulate wheat. They are the pool we can use to spawn new villagers (both Farmers and Warriors).
- Use spawn groups to create additional villagers:
  - spawn farmer: for every two Farmers assigned and 10 wheat, one new Farmer is spawned. To maximize spawning, allocate 4 Farmers to the spawn farmer group when possible (two spawns) and ensure wheat is sufficient (>= 20).
  - spawn warrior: for every two Farmers assigned and 12 wheat, one new Warrior is spawned. If enough Farm wheat is available and there are at least 4 Farmers, we can attempt to spawn 2 Warriors (requires 4 Farmers and 24 wheat). We will implement a conservative approach: spawn up to 2 Warriors when possible (2 farmers in the spawn warrior group, wheat >= 12, or 4 farmers with wheat >= 24 when aiming for 2 spawns).
- In assign_in_cave, keep Warriors attacking (attack group) and move Farmers back to Village (village group) to ensure Farmers stay in the Village.

Implementation notes
- The environment provides:
  - environment.assign_group(component, group_id) to assign a component to a group.
  - environment.farm.wheat to read current wheat.
- We explicitly re-assign every component to exactly one group in both assign_in_village and assign_in_cave, per the required API.

Now the Python implementation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Read current wheat from the Farm
        wheat = 0
        try:
            wheat = getattr(environment.farm, "wheat", 0)
        except Exception:
            wheat = 0

        nf = len(farmers)
        nw = len(warriors)

        # Determine how many to put into spawn groups (disjoint usage of farmers)
        to_spawn_farmer = 0
        to_spawn_warrior = 0

        # Attempt to spawn up to 2 farmers (requires 4 farmers and 20 wheat)
        if nf >= 4 and wheat >= 20:
            to_spawn_farmer = 4  # two new farmers (two spawns)

        # Attempt to spawn up to 2 warriors (requires 4 farmers and 24 wheat if we're using 4 for farmers;
        # otherwise at least 2 farmers and 12 wheat)
        remaining_farmers_for_warrior = nf - to_spawn_farmer
        if remaining_farmers_for_warrior >= 4 and wheat >= 44:
            to_spawn_warrior = 4  # two new warriors (two spawns)
        elif remaining_farmers_for_warrior >= 2 and wheat >= 12:
            to_spawn_warrior = 2  # one new warrior

        # Assign groups
        # Warriors go to cave (to be in Cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers: some go to spawn groups, rest farm
        idx = 0
        # Spawn farmer group
        for _ in range(min(to_spawn_farmer, nf)):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Spawn warrior group (disjoint from spawn farmer)
        for _ in range(min(to_spawn_warrior, nf - idx)):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers stay farming in Village
        for j in range(idx, nf):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: attack with Warriors; Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to Village
                environment.assign_group(c, "village")
```