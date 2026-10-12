Strategy and reasoning

Goal recap:
- All Warriors should go to the Cave and then attack the Dragon.
- All Farmers stay in the Village and either farm or spawn new villagers (Farmers and Warriors are both needed for growth).
- Spawning requires two villagers assigned to a spawn group plus a fixed amount of wheat:
  - spawn farmer: 2 villagers + 10 wheat → 1 new Farmer per pair
  - spawn warrior: 2 villagers + 12 wheat → 1 new Warrior per pair
- We can only assign components to the predefined groups via environment.assign_group(component, group_id).
- You win by reducing the Dragon HP to 0; you lose if 30 steps pass or if all villagers die.

Adaptation design (two-phase approach)
1) In assign_in_village (villagers still in the Village):
   - Warriors: assign to the cave group so they move towards the cave to prepare for attack.
   - Farmers: split into three possible purposes:
     - farm: keep producing wheat
     - spawn farmer: generate new Farmers (needs 2 Farmers and 10 wheat)
     - spawn warrior: generate new Warriors (needs 2 Farmers and 12 wheat)
   - To keep things deterministic and safe, compute how many spawns can occur this step based on current wheat and the number of Farmers:
     - spawn_farmer_pairs = min(number_of_farmers // 2, wheat // 10)
     - spawn_warrior_pairs = min((number_of_farmers - 2*spawn_farmer_pairs) // 2, (wheat - 10*spawn_farmer_pairs) // 12)
   - Assign farmers in input order to: first the spawn_farmer group (in pairs), then the spawn_warrior group (in pairs), and finally the remaining to the farm group. This ensures a gradual, wheat-aware growth of the population while keeping all Warriors preparing in the cave.

2) In assign_in_cave (villagers in the Cave):
   - Warriors: assign to attack the Dragon.
   - Farmers: move back to the Village to continue farming or spawning there.
   - This aligns with the rule that all Warriors should end up attacking, while Farmers remain in the Village.

Implementation notes
- We deterministically split Farmers into spawn groups using current wheat and population size, ensuring we never attempt to spawn more villagers than wheat allows.
- We always move Warriors to the cave in assign_in_village, and in assign_in_cave we direct them to attack.
- The code respects the exact group names provided: farm, cave, spawn farmer, spawn warrior, attack, village.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (will be handled in assign_in_cave)
        - spawn farmer: for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers in this group and 12 wheat, a new Warrior is spawned
        """
        # Classify current farmers and warriors (use safe attribute access)
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Fetch current wheat available for spawning
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0  # If wheat info is unavailable, fall back to zero

        n_farmers = len(farmers)

        # Compute how many spawns we can trigger this step (deterministic and wheat-aware)
        spawn_farmer_pairs = min(n_farmers // 2, wheat // 10)
        spawn_farmer_size = spawn_farmer_pairs * 2  # number of farmers assigned to spawn farmer

        remaining_farmers = n_farmers - spawn_farmer_size
        wheat_after_farmer_spawns = max(0, wheat - spawn_farmer_pairs * 10)

        spawn_warrior_pairs = min(remaining_farmers // 2, wheat_after_farmer_spawns // 12)
        spawn_warrior_size = spawn_warrior_pairs * 2

        # Assign in the order of the input (to be deterministic)
        farmer_index = 0
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors go to the Cave
                environment.assign_group(c, "cave")
            else:
                # Farmers: send to one of the three spawn/farm groups
                if farmer_index < spawn_farmer_size:
                    environment.assign_group(c, "spawn farmer")
                elif farmer_index < spawn_farmer_size + spawn_warrior_size:
                    environment.assign_group(c, "spawn warrior")
                else:
                    environment.assign_group(c, "farm")
                farmer_index += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - attack: Warriors should attack the Dragon
        - cave: Stay in the Cave (not used for Warriors in this strategy)
        - village: Go to the Village (Farmers should return to Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should return to the Village to farm or spawn there
                environment.assign_group(c, "village")
```