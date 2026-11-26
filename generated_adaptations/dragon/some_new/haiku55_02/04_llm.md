## Diagnosis

The previous version had three problems:

1. **Warrior production stopped after step 8.** The spawn rule only ran during `step <= 8`, so the warrior count fell to zero later in the game. Nobody could attack, and the Dragon regenerated.
2. **Farmers were never used for growth.** Early farmer spawning was missing, so the economy stayed small and could not fund warrior spawns.
3. **Spawn pairs were taken only from warriors.** Warriors are the damage dealers, so using two of them for every spawn removed attackers from the fight.

## New strategy

**Village:**
- **Eat:** Villagers with `steps_since_meal >= 3` eat. This keeps a margin below the 6-step starvation limit, even after the trip back from the Cave.
- **Spawn:** Pairs are taken from the farmers first, because farmers are the weaker fighters and still produce wheat. The pair spawns a **warrior** whenever the total warrior count is below a target and there is enough wheat after reserving meals. Otherwise, early in the game, the pair spawns a **farmer** to grow the wheat economy. Warriors are used as a fallback only when there are not enough farmers.
- **Cave / Farm:** Remaining warriors go to the Cave to attack. Remaining farmers stay on the farm.

**Cave:**
- Warriors with `steps_since_meal <= 2` attack, so they never reach starvation while fighting.
- Warriors with `steps_since_meal >= 3` return to the Village to eat.
- Farmers return to the Village to farm. They are fragile and deal little damage.

Every component is assigned exactly once per call, and each spawn targets a valid group.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Villagers in the Village with steps_since_meal >= 3 eat (safe margin below 6).
    - Spawning uses pairs of farmers first (farmers are weak fighters and the
      economy is preserved by keeping warriors in the fight):
        * spawn warrior whenever total warriors < WARRIOR_TARGET and wheat allows;
        * early on, spawn farmers to grow the wheat economy.
      Warriors are only used as spawn pair members when there are not enough farmers.
    - Remaining warriors go to the Cave and attack while steps_since_meal <= 2.
    - Villagers in the Cave with steps_since_meal >= 3 (and all farmers) return
      to the Village.
    """

    EAT_THRESHOLD = 3          # eat in village when hunger reaches this
    RETURN_THRESHOLD = 3       # leave cave to eat when hunger reaches this
    WARRIOR_TARGET = 8         # total warriors we want alive
    FARMER_TARGET = 6          # total farmers we want alive
    EARLY_FARMER_STEP = 10     # farmer spawning only in early game

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat = [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD]
        rest = [c for c in components if c.steps_since_meal < self.EAT_THRESHOLD]

        wheat_avail = wheat - len(eat)
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)

        farmers = [c for c in rest if c.role == "Farmer"]
        warriors = [c for c in rest if c.role == "Warrior"]

        assignment = {}
        for c in eat:
            assignment[id(c)] = "eat"

        spawn_members = []
        spawn_group = None

        # Prefer spawning a warrior (uses 12 wheat) while below the warrior target
        if total_warriors < self.WARRIOR_TARGET and wheat_avail >= 12:
            pool = farmers + warriors  # farmers first
            if len(pool) >= 2:
                spawn_members = pool[:2]
                spawn_group = "spawn warrior"
                wheat_avail -= 12
        # Otherwise, early in the game, grow the economy with a farmer (10 wheat)
        if spawn_group is None and step <= self.EARLY_FARMER_STEP \
                and total_farmers < self.FARMER_TARGET and wheat_avail >= 10:
            pool = farmers + warriors
            if len(pool) >= 2:
                spawn_members = pool[:2]
                spawn_group = "spawn farmer"
                wheat_avail -= 10

        spawn_ids = set(id(c) for c in spawn_members)
        for c in spawn_members:
            assignment[id(c)] = spawn_group

        for c in rest:
            if id(c) in spawn_ids:
                continue
            if c.role == "Warrior":
                assignment[id(c)] = "cave"
            else:
                assignment[id(c)] = "farm"

        for c in components:
            environment.assign_group(c, assignment[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETURN_THRESHOLD or c.role != "Warrior":
                environment.assign_group(c, "village")
            elif c.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")
```