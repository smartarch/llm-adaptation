Reasoning and strategy planning

- Objectives and constraints
  - All Warriors should go to the Cave to attack the Dragon.
  - All Farmers should stay in the Village.
  - Spawn groups exist to grow your force: "spawn farmer" (needs 2 villagers in the group and 10 wheat) and "spawn warrior" (needs 2 villagers in the group and 12 wheat).
  - You win by killing the Dragon (Dragon starts at 50 HP).
  - The Dragon must be attacked at least once in the first 15 steps.
  - You should have both more farmers and more warriors spawned so the Dragon is killed quickly.
  - You want to keep at least half of the Warriors in the Cave so they can attack during the encounter.

- Strategy overview
  - Immediately ensure all Warriors are assigned to the cave to attack the Dragon, and Farmers stay in the Village to farm.
  - Use the spawn groups to incrementally grow your force without violating the constraints:
    - Spawn Farmer: Move a small number of Farmers from farming to the "spawn farmer" group, but leave at least two Farmers actively farming to continue producing wheat (needed for spawning).
    - Spawn Warrior: If there is enough wheat in the Farm and there are at least two Farmers available to reassign, move two of the farming Farmers to the "spawn warrior" group to trigger spawning a Warrior (as long as we still have enough Farmers left to farm and produce wheat).
  - Early attack guarantee: By assigning all Warriors to the cave for immediate attack, the Dragon will be attacked in the first steps (the exact timing depends on the game loop, but this guarantees an early assault).
  - Cave management: In the Cave, keep Warriors attacking the Dragon; Farmers should go back to the Village.

- How this maps to the components and actions
  - In assign_in_village:
    - Farmers: default to "farm".
    - Warriors: default to "cave".
    - If step <= 15 and there are at least 4 Farmers, move two Farmers to "spawn farmer" (to trigger spawning new Farmers while still keeping some farming).
    - If step <= 15 and farm wheat >= 12 and there are at least 2 Farmers available in farming, move two Farmers from farming to "spawn warrior" (to trigger spawning new Warriors).
  - In assign_in_cave:
    - Warriors: move to "attack" (they attack the Dragon).
    - Farmers: move to "village" (return to Village to continue farming or spawn elsewhere).

- Why this is likely to work
  - It fulfills the requirement that Warriors end up in the Cave to attack and Farmers stay in the Village.
  - It uses spawn groups to grow your force without starving the farm of wheat.
  - It ensures an early attack by forcing Warriors into the Cave from the start.
  - It keeps a reasonable fraction of Warriors in the Cave to maximize attack potential over time.

Now, here is the Python implementation.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Prepare a provisional assignment map
        assignment = {}

        # Default actions: Farmers stay in village to farm, Warriors go to cave
        for f in farmers:
            assignment[f] = "farm"
        for w in warriors:
            assignment[w] = "cave"

        # Spawn strategy:
        #  - Try to spawn two farmers if we have enough farmers to spare and we are still early (step <= 15)
        #  - Then try to spawn warriors if enough wheat is available and we still have farmers to spare
        if step <= 15 and len(farmers) >= 4:
            # Find those farmers currently in farming
            farming_left = [f for f in farmers if assignment.get(f) == "farm"]
            # Move up to 2 farmers to the spawn farmer group, leaving at least 2 farming
            to_move = min(2, max(0, len(farming_left) - 2))
            for i in range(to_move):
                assignment[farming_left[i]] = "spawn farmer"

        # Attempt to spawn warriors if wheat is available and we have enough farmers to spare
        if step <= 15 and getattr(environment.farm, "wheat", 0) >= 12:
            farming_left = [f for f in farmers if assignment.get(f) == "farm"]
            if len(farming_left) >= 2:
                for i in range(min(2, len(farming_left))):
                    assignment[farming_left[i]] = "spawn warrior"

        # Apply the determined group assignments
        for comp in components:
            group = assignment.get(comp, "farm")  # default to farm if not specified
            environment.assign_group(comp, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: all Warriors should attack, Farmers should go back to the Village
        for comp in components:
            if getattr(comp, "role", None) == "Warrior":
                environment.assign_group(comp, "attack")
            else:
                environment.assign_group(comp, "village")
```