Reasoning and updated strategy

Goal reinforcement
- Keep all Warriors in the Cave to attack the Dragon as soon as possible.
- Keep Farmers in the Village to farm and to enable spawning via the spawn groups.
- Spawn events should be as productive as possible this step to accelerate growth and DPS, but without starving farming.
- Attack should occur early (within the first 15 steps) and have enough Warriors in the Cave to maximize DPS.

What’s improved
- Spawn optimization per step: Instead of greedily choosing farm-spawns first and then warrior-spawns, we now compute the optimal combination of spawn farmer and spawn warrior events that maximizes the total number of spawn events this step under the constraints:
  - Each spawn event uses 2 farmers (from the village) and consumes 10 wheat (for a Farmer) or 12 wheat (for a Warrior).
  - We cannot exceed the number of available farmers.
  - We cannot exceed the available wheat in the Farm.
- This explicit small integer optimization yields more spawned villagers this step when possible, accelerating growth sooner while still preserving Warriors in the Cave for early attack.

Strategy outline
- assign_in_village:
  - Move all Warriors to the Cave (group "cave") so they will be ready to attack.
  - Let F be the number of Farmers in the Village and W be the Wheat in environment.farm.wheat.
  - Compute the best (k1, k2) where:
    - k1 = number of spawn farmer events this step
    - k2 = number of spawn warrior events this step
    - Constraints: 2*(k1 + k2) <= F and 10*k1 + 12*k2 <= W
    - Objective: maximize k1 + k2; break ties by preferring more warrior spawns (larger k2)
  - Assign 2*k1 farmers to "spawn farmer", 2*k2 farmers to "spawn warrior", and the remaining farmers to "farm".
  - Assign all Warriors to "cave" (they are in cave already, but the code must explicitly place them).
- assign_in_cave:
  - All Warriors go to "attack".
  - All Farmers go to "village".

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _best_spawn_distribution(self, num_farmers, wheat):
        """
        Brute-force search for the best (k1, k2) where:
          - k1: number of spawn farmer events
          - k2: number of spawn warrior events
          Constraints:
            2*(k1 + k2) <= num_farmers
            10*k1 + 12*k2 <= wheat
          Objective:
            maximize (k1 + k2); tie-break prefer larger k2 (more warrior spawns)
        Returns tuple (k1, k2)
        """
        best_k1, best_k2 = 0, 0
        best_total = 0
        max_possible = num_farmers // 2
        for k1 in range(0, max_possible + 1):
            for k2 in range(0, max_possible - k1 + 1):
                if 10 * k1 + 12 * k2 <= wheat:
                    total = k1 + k2
                    if total > best_total:
                        best_total = total
                        best_k1, best_k2 = k1, k2
                    elif total == best_total:
                        # tie-break: prefer more warrior spawns
                        if k2 > best_k2:
                            best_k1, best_k2 = k1, k2
        return best_k1, best_k2

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - farm: Farmers stay in the Village to farm
        - cave: Warriors go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default allocations
        to_farm = []
        to_cave = []
        to_spawn_farmer = []
        to_spawn_warrior = []

        # All Warriors should head to the Cave to attack
        to_cave.extend(warriors)

        # Farmers present in village
        available_farmers = list(farmers)
        num_farmers = len(available_farmers)

        # Wheat available in the Farm
        wheat = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            wheat = getattr(farm_env, "wheat", 0)

        # Compute best spawn distribution this step
        k1, k2 = self._best_spawn_distribution(num_farmers, wheat)

        # Allocate farmers for spawns
        take_for_farm = 2 * k1
        take_for_warrior = 2 * k2

        to_spawn_farmer = available_farmers[:take_for_farm]
        to_spawn_warrior = available_farmers[take_for_farm: take_for_farm + take_for_warrior]

        # Remaining farmers go to farm
        to_farm = available_farmers[take_for_farm + take_for_warrior:]

        # Assign groups
        for c in to_farm:
            environment.assign_group(c, "farm")
        for c in to_spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave (not used in this strategy, but kept for completeness)
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")
```