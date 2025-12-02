Strategy and reasoning (updated)

- Problem with the previous approach
  - While it ensured every component was assigned exactly once, it relied on spawning as soon as possible, which can starve early wheat production. In some runs this led to slow DPS, high villager death risk, and zero wins within the simulated horizon.

- Improved strategy goals
  - Ensure a quick, reliable attack on the Dragon by having Warriors in the Cave as early as possible.
  - Balance farming and spawning to accelerate wheat accumulation while still creating extra fighters.
  - Use step-aware logic: early steps (1-3) prioritize wheat accumulation by farming; after that, spawn as wheat allows, but keep some farmers farming to sustain wheat income for future spawns.
  - Maintain the rule that every component is assigned exactly once per step.

- How the updated strategy works
  - assign_in_village:
    - Always send all existing Warriors to the Cave (to travel and attack).
    - In early steps (step <= 3) or when there are no farmers, assign all farmers to farm to grow wheat.
    - After step 3, attempt to spawn new villagers:
      - Reserve a portion of farmers for ongoing farming to keep wheat coming in.
      - Use the remaining farmers to spawn:
        - First, as many farmer-spawns as possible (needs 2 farmers + 10 wheat per spawn).
        - Then, as many warrior-spawns as possible (needs 2 farmers + 12 wheat per spawn).
      - All farmers are assigned in a single pass to one of: "spawn farmer", "spawn warrior", or "farm".
  - assign_in_cave:
    - Warriors attack (group "attack"), Farmers go back to village (group "village").
    - This keeps the Dragon under attack while preserving farming capacity in the Village.

- Why this helps win faster
  - Early farming creates wheat for subsequent spawns, enabling a faster buildup of frontline warriors.
  - Rapid introduction of warriors increases the chance to deal more DPS to the Dragon earlier, while still keeping enough Farmers to sustain wheat gains for ongoing spawns.
  - Ensuring at least some Warriors reach the cave early increases the likelihood of hitting the Dragon within the first 15 steps.

Updated Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate existing farmers and warriors in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Move all existing warriors to the cave to start marching towards the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Early steps: focus on farming to accumulate wheat
        if step <= 3 or len(farmers) == 0:
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Reserve a fraction of farmers for ongoing farming (to sustain wheat production)
        reserve = max(1, int(len(farmers) * 0.25))

        # Potential spawner farmers are those not reserved for ongoing farming
        potential_spawners = farmers

        # Farmer-spawns: need 2 farmers + 10 wheat per spawn
        f_spawns = min((len(potential_spawners) - reserve) // 2 if len(potential_spawners) > reserve else 0,
                       wheat // 10)

        wheat_after_f_farm = wheat - f_spawns * 10

        # Warrior-spawns: need 2 farmers + 12 wheat per spawn
        remaining_for_w_spawns = max(0, len(potential_spawners) - reserve - 2 * f_spawns)
        w_spawns = min(remaining_for_w_spawns // 2, wheat_after_f_farm // 12)

        # Assign each farmer to exactly one group in a single pass
        # First 2*f_spawns farmers -> "spawn farmer"
        # Next 2*w_spawns farmers -> "spawn warrior"
        # Remaining farmers (including those reserved for farming) -> "farm"
        total_farmers = len(farmers)
        for idx, f in enumerate(farmers):
            if idx < 2 * f_spawns:
                environment.assign_group(f, "spawn farmer")
            elif idx < 2 * f_spawns + 2 * w_spawns:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack with warriors; farmers go back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```