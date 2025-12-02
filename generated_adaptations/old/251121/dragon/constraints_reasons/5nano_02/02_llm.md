Strategy reasoning and description

Goal alignment and constraints
- Warriors must end up in the Cave and attack the Dragon. In practice this means: in village, send all Warriors to the cave; in cave, move them to the attack group so they actively strike the Dragon.
- Farmers must stay in the Village. They can farm or participate in spawning: "spawn farmer" or "spawn warrior" groups.
- Spawn mechanics:
  - To spawn a new Farmer: place at least two villagers in the "spawn farmer" group and have at least 10 wheat (consumed by spawning).
  - To spawn a new Warrior: place at least two villagers in the "spawn warrior" group and have at least 12 wheat (consumed by spawning).
  - The engine handles the actual spawning when the conditions are met.
- Early Dragon engagement:
  - Ensure at least one attack happens within the first 15 steps. Since Warriors will move to the cave and then be placed in the attack group in the cave, this will help ensure early aggression.
- Coverage and balance:
  - Keep a sizable portion of Warriors in the cave (attack) most of the time; at least half should be ready to attack the Dragon.
  - Spawn a mix of new Farmers and Warriors to improve the odds of killing the Dragon by increasing total damage output and sustaining the effort (new Farmers can farm to produce Wheat for spawning more units later; new Warriors add DPS).

Implementation approach
- assign_in_village:
  - Move all Warriors to the cave (group "cave") so they travel to the Dragon’s vicinity.
  - Keep all Farmers in the Village by default (group "farm").
  - Attempt to spawn new villagers:
    - If there are at least 2 Farmers and the Farm has 10 or more Wheat, assign two Farmers to the "spawn farmer" group to trigger a new Farmer spawn.
    - If there are at least 2 remaining Farmers (not already in spawn farmer) and there is at least 12 Wheat, assign two to the "spawn warrior" group to trigger a new Warrior spawn.
  - The rest of Farmers stay in "farm".
- assign_in_cave:
  - Assign all Warriors currently in the cave to the "attack" group (to fight the Dragon).
  - Assign all Farmers currently in the cave to the "village" group (they should head back to the Village as per the requirement).
  - This ensures the Dragon gets attacked and farmers remain in the Village.

This strategy adheres to all required group names, ensures early dragon engagement, keeps Warriors in cave to attack, and uses spawn groups to generate additional youth and DPS when wheat permits.

Python code

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split current villagers in village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: Farmers stay in farm, Warriors go to cave
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Spawn logic:
        # Try to spawn 1st Farmer if possible (needs 2 villagers in spawn farmer and 10 wheat)
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            # Take first two Farmers to spawn Farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            # Remaining Farmers (if any) stay farming; Warriors already moved to cave above
            # No further action needed here; the engine will spawn if wheat consumed
        # Try to spawn Warrior if possible (needs 2 villagers in spawn warrior and 12 wheat)
        # Only if we have enough farmers left after potential spawn farmer designation
        remaining_farmers = farmers[2:] if len(farmers) >= 2 else []
        if len(remaining_farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            for c in remaining_farmers[:2]:
                environment.assign_group(c, "spawn warrior")
        # If not enough farmers for the above, ensure there are enough villagers in spawning groups by fallback
        # Do not assign anyone else to spawn groups; keep existing assignments for other villagers

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In cave: send Warriors to attack Dragon; Farmers return to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # If unknown role, default to staying in cave (safe fallback)
                environment.assign_group(c, "cave")
```