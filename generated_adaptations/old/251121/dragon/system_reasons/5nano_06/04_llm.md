Reasoning and strategy

Goal and constraints recap:
- All Warriors must go to the Cave and attack the Dragon.
- All Farmers should stay in the Village (but can be assigned to spawning groups to create new villagers).
- We should attack early (at least once within the first 15 steps).
- We want to spawn new Farmers and Warriors to increase DPS and wheat production, but spawning requires both group membership and sufficient wheat.
- To win, the Dragon must die as soon as possible; we should bias towards increasing DPS early while maintaining enough farming to sustain spawning.

What changed in this improved strategy:
- Aggressive but controlled early spawning: as soon as we have enough farmers and wheat, we assign some farmers to spawn warrior and spawn farmer groups to generate new Warriors and Farmers early. This increases DPS earlier and increases wheat throughput for future spawns.
- Always ensure all Warriors are in the Cave and will attack; Farmers stay in the Village, farming or enabling spawning.
- Spawning thresholds are kept small to avoid starving wheat or stalling early attacks:
  - If there are at least 4 farmers and wheat >= 12, allocate 2 farmers to the spawn warrior group (to generate at least one new Warrior quickly).
  - If after that we still have at least 4 more farmers and wheat >= 20, allocate 4 more farmers to the spawn farmer group (to generate up to 2 new Farmers subsequently).
- This approach aims to ensure:
  - Attacks happen early (via Warriors in cave).
  - The Dragon takes DPS from the get-go.
  - New villagers appear to boost both DPS and wheat production in subsequent steps.
  - No Farmers end up permanently stuck in the Cave; they remain in Village unless assigned to spawning groups.

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors must go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available in Farm (read-only in this interface)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 2) Spawn logic (aggressive but gated by wheat and population)
        idx = 0  # index into farmers list for assigning to spawn groups

        # Step-based gating: try to spawn a Warrior early if possible
        # Condition: at least 4 farmers and enough wheat (>=12)
        if len(farmers) - idx >= 4 and wheat >= 12:
            for _ in range(2):  # assign two farmers to spawn warrior
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Spawn farmers if we have enough farmers left and enough wheat
        # Condition: at least 4 remaining farmers and wheat >= 20
        if len(farmers) - idx >= 4 and wheat >= 20:
            for _ in range(4):  # assign four farmers to spawn farmer (produces up to 2 new farmers)
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers stay in the village and farm
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # All farmers not explicitly reassigned remain in farm by default
        # (explicit assignments above ensure correct grouping)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: all Warriors attack the Dragon; Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```