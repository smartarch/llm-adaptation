Strategy and reasoning (what I plan to implement and why)

Goal alignment:
- All Warriors should go to the Cave and attack the Dragon.
- All Farmers should stay in the Village (but can participate in spawning new villagers).
- Spawn mechanics: For every two villagers assigned to a spawn group and enough wheat, a new villager is spawned (10 wheat for farmers, 12 wheat for warriors). We’ll utilize this to grow both farmers and warriors gradually.
- Early aggression: The Dragon should be attacked at least once within the first 15 steps.
- Balance: We want a few extra farmers and a few extra warriors to increase DPS and wheat generation.

How the adaptation works across phases:
- Village phase (assign_in_village):
  - Warriors are moved to the Cave immediately (to ensure they eventually attack the Dragon). They will be reclassified in the cave phase to the “attack” group, but moving them to the cave now guarantees presence in the cave early.
  - Farmers stay in the Village and farm by default (group "farm").
  - Spawn groups (spawn farmer, spawn warrior) are used opportunistically to grow the population if there is enough wheat:
    - If there are at least 2 farmers and the Farm’s wheat >= 10, move two farmers into the "spawn farmer" group.
    - If after that there are at least 2 other farmers and wheat >= 12, move two more farmers into the "spawn warrior" group.
    - The remaining farmers stay in "farm".
  - This strategy ensures:
    - Farmers keep farming to generate wheat for future spawns.
    - Some farmers are provisioning new villagers (both farmers and warriors) when wheat allows.
    - Warriors are kept in the village only long enough to move to the cave in the next phase, ensuring they eventually attack.

- Cave phase (assign_in_cave):
  - All Warriors currently in the Cave are assigned to the "attack" group to actively attack the Dragon.
  - Farmers in the Cave are assigned to "village" to return to the Village (preserving the rule that Farmers stay in Village).

Why this meets requirements:
- Dragon must be killed: Spawning extra farmers and warriors increases DPS in cave and increases the chance to kill the Dragon within 30 steps.
- Attack early: Warriors are sent to the cave at the Village phase, and in the Cave phase they are moved to "attack" immediately, ensuring an attack early (even on step 0 after first transition).
- All warriors go to the Cave: In Village phase, Warriors are moved to cave; in Cave phase they join the attack group.
- All farmers stay in Village: Farmers are kept in "farm" or in spawn groups, and only return to Village from cave at the Cave phase.
- Spawn some of both types: Spawn groups are used when wheat is sufficient to create a few extra farmers and warriors.
- Most warriors in cave and attacking: We place Warriors in cave and then in attack, aligning with the requirement to have many in cave to attack.

Code (Python) that implements the strategy

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to groups:
        - All Warriors -> cave (to move to cave)
        - Farmers -> farm by default
        - Optional spawns:
          * If at least 2 farmers and wheat >= 10, assign 2 farmers to "spawn farmer"
          * If after that at least 2 other farmers and wheat >= 12, assign 2 to "spawn warrior"
        """
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: all farmers stay in village and farm
        for f in farmers:
            environment.assign_group(f, "farm")

        # Move all Warriors to cave (they will be re-assigned to attack in assign_in_cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawn logic (spawn groups operate in village phase)
        assigned = set()

        # Try to spawn farmers: pick first two farmers if wheat allows
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn farmer")
                assigned.add(f)

        # Try to spawn warriors: use next two farmers if wheat allows
        remaining_farmers = [f for f in farmers if f not in assigned]
        if len(remaining_farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            for f in remaining_farmers[:2]:
                environment.assign_group(f, "spawn warrior")
                assigned.add(f)

        # Any remaining farmers (not assigned to spawn groups) stay in farm
        for f in farmers:
            if f in assigned:
                continue
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to groups:
        - Warriors -> attack (attack the Dragon)
        - Farmers -> village (return to Village)
        """
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            elif role == "Farmer":
                environment.assign_group(comp, "village")
            else:
                # Fallback: keep sensible default
                environment.assign_group(comp, "village")
```