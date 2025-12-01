Reasoning and strategy

- Objective and constraints recap
  - All Warriors must go to the Cave (and then attack the Dragon).
  - All Farmers must stay in the Village (but can farm or participate in spawning).
  - Spawn mechanics: For every 2 villagers assigned to a spawn group and a required amount of wheat, the corresponding new villager is spawned:
    - spawn farmer: needs 2 villagers in the group and 10 wheat → spawns a new Farmer.
    - spawn warrior: needs 2 villagers in the group and 12 wheat → spawns a new Warrior.
  - You win by killing the Dragon (Dragon HP 50). Dragon can attack back; you should attack at least once within the first 15 steps.
  - You want to keep most Warriors in the Cave to attack, and you want to spawn a few extra Farmers and Warriors to increase DPS and survivability.

- Strategy overview
  - Village stage (assign_in_village)
    - Move all existing Warriors to the Cave by assigning them to the cave group (they will eventually attack in the Cave stage).
    - Keep Farmers in Village, but use some of them as spawners to generate additional villagers:
      - Use 2 Farmers per “spawn farmer” spawn (needs 10 wheat) to generate extra Farmers.
      - Use 2 Farmers per “spawn warrior” spawn (needs 12 wheat) to generate extra Warriors.
    - Distribute Farmers between:
      - spawn farmer (to generate more Farmers)
      - spawn warrior (to generate Warriors)
      - farm (to continue farming wheat)
    - The exact numbers should respect available wheat and available Farmers: s_farm = min(Farmers // 2, Wheat // 10); s_war = min((Farmers - 2*s_farm) // 2, (Wheat - 10*s_farm) // 12). This yields a simple, delta-based spawning plan while preserving most Farmers for farming.
  - Cave stage (assign_in_cave)
    - Move all Warriors to the attack group (they will attack the Dragon).
    - Move all Farmers back to the village group (they stay in the Village).

- Why this works
  - Ensures all Warriors are in the Cave and ready to attack as soon as the Cave phase begins.
  - Spawns a few additional Farmers and Warriors to ramp up DPS without leaving Farmers entirely the Village.
  - Maintains the “half of Warriors in Cave most of the time” by keeping Warriors in cave/attack as a constant during the Cave phase.
  - Keeps the early attack requirement by having Warriors in the Cave and attacking soon after the first Cave turn.

Code implementation

```py
from generated_adaptations.base_classes.drag on import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Village villagers into:
        - farm: stay in Village and farm
        - cave: go to the Cave (to join attack later)
        - spawn farmer: for every two villagers assigned and 10 wheat, spawn a new Farmer
        - spawn warrior: for every two villagers assigned and 12 wheat, spawn a new Warrior
        """
        # Separate current villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        n_farmers = len(farmers)
        n_warriors = len(warriors)

        # Wheat available for spawning (from the Farm)
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = int(getattr(environment.farm, "wheat") or 0)

        # Spawning plan (as many as possible given wheat and farmer availability)
        # s_farm: number of 2-farmer groups we will assign to "spawn farmer"
        s_farm = min(n_farmers // 2, wheat // 10)

        remaining_farmers_after_farm_spawns = n_farmers - (2 * s_farm)

        # s_war: number of 2-farmer groups we will assign to "spawn warrior"
        # Ensure we have enough farmers left for these spawns and enough wheat left
        wheat_after_farm = wheat - (10 * s_farm)
        s_war = min(remaining_farmers_after_farm_spawns // 2, max(0, wheat_after_farm // 12))

        # Assign groups
        # First 2*s_farm farmers -> "spawn farmer"
        idx = 0
        for i in range(2 * s_farm):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Next 2*s_war farmers -> "spawn warrior"
        for i in range(2 * s_war):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers -> "farm" (stay in Village and farm)
        for i in range(idx, n_farmers):
            environment.assign_group(farmers[i], "farm")

        # All Warriors should go to the Cave (to join the attack)
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Cave villagers into:
        - attack: Warriors attack the Dragon
        - cave: (optional) stay in cave (we'll not use this for Warriors)
        - village: Farmers go back to Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # Warriors should attack the Dragon once in the Cave
                environment.assign_group(c, "attack")
            else:
                # Farmers stay in Village
                environment.assign_group(c, "village")
```