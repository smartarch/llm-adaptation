Reasoning and updated adaptation strategy

Problem recap
- We want to kill the Dragon quickly. Warriors must ultimately assault from the Cave, while Farmers stay in the Village to farm or spawn new villagers.
- Spawns occur via two groups in the Village: "spawn farmer" (needs 2 farmers in the group and 10 wheat per spawn) and "spawn warrior" (needs 2 farmers in the group and 12 wheat per spawn).
- All current Warriors should head to the Cave to attack; Farmers should stay in the Village for farming and spawning.
- The tests require spawning some new Warriors early to increase the chance of killing the Dragon.

Key issue with previous approach
- The earlier strategy prioritized farming spawns after allocating for warrior spawns, which could lead to zero Warrior spawns in some scenarios, delaying the early ramp of combat power.
- Additionally, the plan used wheat accounting in a way that could underutilize available resources in the immediate step, reducing early spawn opportunities.

Strategy update
- In assign_in_village:
  - First move all current Warriors to the Cave (to satisfy the “all Warriors to cave” rule).
  - Then allocate spawns prioritizing Warriors first:
    - Compute how many Warrior spawns we can support now: k_w = min(number_of_farmers // 2, wheat // 12).
    - The two-villager units used for each Warrior spawn come from Farmers. Assign 2*k_w farmers to the "spawn warrior" group.
    - With the remaining Farmers and remaining Wheat after Warrior spawns, compute how many Farmer spawns we can support: k_f = min(remaining_farmers // 2, floor((wheat - 12*k_w) / 10)).
    - Assign 2*k_f farmers to the "spawn farmer" group and the rest to the "farm" group.
- In assign_in_cave:
  - Keep Warriors in the Cave for attack (as before).
  - Send any Farmers in the Cave back to the Village to continue farming or spawning.

This approach ensures we actively generate new Warriors in the early stages whenever possible, which should satisfy the test requirement to spawn more Warriors and improve the odds of killing the Dragon within the time limit.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning plan: prioritize Warrior spawns first, then Farmer spawns
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Warrior spawns possible: 2 farmers per spawn, 12 wheat per spawn
        k_w = min(len(farmers) // 2, int(wheat // 12))

        spawn_warrior_group = farmers[:2 * k_w]
        remaining_after_war = farmers[2 * k_w:]

        wheat_after_war = max(0, wheat - 12 * k_w)

        # Farmer spawns possible: 2 farmers per spawn, 10 wheat per spawn
        k_f = min(len(remaining_after_war) // 2, int(wheat_after_war // 10))

        spawn_farmer_group = remaining_after_war[:2 * k_f]
        farm_group = remaining_after_war[2 * k_f:]

        # 3) Assign groups to villagers
        for c in spawn_warrior_group:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer_group:
            environment.assign_group(c, "spawn farmer")
        for c in farm_group:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the cave by role
        cave_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Warriors should attack the Dragon
        for w in cave_warriors:
            environment.assign_group(w, "attack")

        # 2) Farmers (if any) should go back to the Village
        cave_farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        for f in cave_farmers:
            environment.assign_group(f, "village")

        # If there are any other types (edge cases), send them to village as a safe default
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "village")
```