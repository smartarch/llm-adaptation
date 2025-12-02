"""
Adaptation strategy reasoning:

- Objective: Kill the Dragon as fast as possible within 30 steps.
- Observations:
  - Warriors are stronger (3 damage per attack) but start in Village and must travel to Cave to fight.
  - Farmers are weaker (1 damage per attack) but can stay in Village to farm or spawn more villagers when enough wheat is available.
  - Spawning rules:
      - spawn farmer: for every 2 villagers in the "spawn farmer" group and at least 10 wheat, a new Farmer is spawned.
      - spawn warrior: for every 2 villagers in the "spawn warrior" group and at least 12 wheat, a new Warrior is spawned.
  - The Dragon can damage villagers in cave, and villagers can die. We must minimize deaths while maximizing DPS.
  - All Warriors should end up in the Cave to attack the Dragon; Farmers should remain in Village to farm or spawn more villagers.

- Strategy outline:
  1) In village:
     - Put all Warriors in the "cave" group so they travel to the Dragon and start attacking.
     - For Farmers, use a simple growth heuristic:
         - If there are at least 2 farmers and current wheat >= 10, assign two farmers to the "spawn farmer" group to spawn a new Farmer (increasing future farming capacity).
         - With remaining farmers, if there is enough wheat (>= 12) and at least 2 farmers remain, spawn a Warrior by assigning two farmers to the "spawn warrior" group to create an additional combatant.
         - All remaining farmers go to the "farm" group to produce wheat.
     - This keeps wheat production ongoing to finance spawning, gradually increasing DPS while keeping deaths low early on.
  2) In cave:
     - All Farmers in Cave should go back to Village (to avoid unnecessary risk and to keep farming), while Warriors stay in Cave and attack (assigned to "attack").
     - This ensures Warriors contribute to DPS while Farmers stay productive in the Village.

- Rationale:
  - The policy ensures Warriors are deployed to maximize early DPS, which is crucial to ending the Dragon quickly.
  - Spawning decisions are constrained by wheat and number of available farmers, balancing resource growth with combat power.
  - Farmers' primary role remains farming to sustain wheat stock for spawning and ongoing production of villagers.

Implementation details:
- The class SmartAdaptation derives from the provided DragonHuntAdaptation base class.
- assign_in_village implements the described Wheat-aware spawning and farming logic.
- assign_in_cave ensures Warriors attack and Farmers return to the Village.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - "farm": Farmers that stay and farm
        - "cave": Warriors that should go to the Cave
        - "spawn farmer": For every two villagers assigned here and 10 wheat, spawn a new Farmer
        - "spawn warrior": For every two villagers assigned here and 12 wheat, spawn a new Warrior
        """
        # Separate by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors go to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available in the Farm
        wheat = getattr(environment, "farm").wheat if hasattr(environment, "farm") else 0

        # 2) Spawn farmer if possible: need at least 2 farmers and 10 wheat
        spawn_farmer_assigned = []
        if len(farmers) >= 2 and wheat >= 10:
            # Assign first two farmers to spawn farmer
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
            spawn_farmer_assigned = farmers[:2]

        # 3) Determine remaining farmers after spawn farmer
        remaining = [c for c in farmers if c not in spawn_farmer_assigned]

        # 4) Spawn warrior if possible: need at least 2 farmers and 12 wheat
        spawn_warrior_assigned = []
        if len(remaining) >= 2 and wheat >= 12:
            for c in remaining[:2]:
                environment.assign_group(c, "spawn warrior")
            spawn_warrior_assigned = remaining[:2]

        # 5) All other farmers go to farm
        for c in farmers:
            if c in spawn_farmer_assigned or c in spawn_warrior_assigned:
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, divide villagers as:
        - "attack": Warriors attack the Dragon
        - "cave": Stay in the Cave (for any Warriors that should remain, though we prefer to move Farmers back)
        - "village": Go to the Village (Farmers return to village)
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")