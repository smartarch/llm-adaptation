## Strategy: Balanced Spawning with Constant Warrior Pressure

The strategy is built around the two goals of killing the Dragon quickly and keeping the village alive.

**Village phase (`assign_in_village`):**
- **Warriors always go to the Cave** (`"cave"`). They deal 3 damage per attack, so they are the main source of Dragon damage. Newly spawned warriors are sent to the Cave on the next step.
- **Farmers stay on the farm by default** (`"farm"`), since they are the wheat economy that pays for future spawns.
- **Spawning uses a wheat budget.** The strategy reads `environment.farm.wheat` and spends it in priority order:
  1. If there is at least 12 wheat and at least 2 farmers, two farmers are sent to `"spawn warrior"`. Warriors are prioritized because they deal more damage.
  2. If wheat remains at least 10 and at least 2 farmers are still available, two farmers are sent to `"spawn farmer"` to grow the economy. This is limited to the early game (steps 0–12) so that enough farmers keep producing wheat afterward.
- Every component receives exactly one assignment, so nothing is left in an undefined group.

**Cave phase (`assign_in_cave`):**
- **Warriors attack** (`"attack"`) every step, which satisfies the requirement that they attack once they reach the Cave. This also ensures the Dragon is hit within the first 15 steps.
- **Any farmer in the Cave is sent back** to `"village"`, since farmers should not fight.
- Any unexpected component defaults to `"cave"` so that no villager is left unassigned.

**How the requirements are met:**
- The Dragon is attacked early because warriors start moving to the Cave on step 0.
- Farmers stay in the Village, and warriors gather in the Cave.
- Both farmers and warriors are spawned when wheat allows.
- Most warriors stay in the Cave during the fight, since only farmers are ever moved out.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors always go to the Cave and attack the Dragon.
    - Farmers stay in the Village on the farm by default.
    - Wheat is spent to spawn warriors first (more damage), then farmers
      (economy) during the early game.
    - Any farmer found in the Cave is sent back to the Village.
    """

    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    EARLY_GAME_STEPS = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors go to the cave to fight the dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Default: farmers work the farm.
        available_farmers = list(farmers)
        assigned_farmers = set()

        # Spawn warriors first (stronger attackers), needs 2 villagers + 12 wheat.
        if wheat >= self.WARRIOR_SPAWN_COST and len(available_farmers) >= 2:
            for f in available_farmers[:2]:
                environment.assign_group(f, "spawn warrior")
                assigned_farmers.add(id(f))
            wheat -= self.WARRIOR_SPAWN_COST
            available_farmers = [f for f in available_farmers if id(f) not in assigned_farmers]

        # Spawn farmers during the early game to grow the economy.
        if (step <= self.EARLY_GAME_STEPS
                and wheat >= self.FARMER_SPAWN_COST
                and len(available_farmers) >= 2):
            for f in available_farmers[:2]:
                environment.assign_group(f, "spawn farmer")
                assigned_farmers.add(id(f))
            wheat -= self.FARMER_SPAWN_COST
            available_farmers = [f for f in available_farmers if id(f) not in assigned_farmers]

        # Remaining farmers stay on the farm.
        for f in available_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Warriors keep attacking the dragon.
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers do not fight; send them back to the village.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")
```