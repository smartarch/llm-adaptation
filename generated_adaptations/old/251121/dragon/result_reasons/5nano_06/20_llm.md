Reasoning and new approach:

- Goal: Kill the Dragon as fast as possible while strictly following the constraints (All Warriors should eventually go to the Cave to attack; All Farmers stay in the Village; Spawns require two villagers in a spawn group and wheat; Dragon can attack back; 30-step loss condition).
- Core idea of the improvement:
  - Guarantee an early but controlled Dragon engagement by sending a small, fixed number of Warriors into the Cave very early (to start denting the Dragon HP) while keeping most of the population in the Village to sustain wheat production.
  - Use spawning conservatively and deterministically, with disjoint donors for each spawn type to avoid pulling villagers away from the Cave in a way that weakens early DPS.
  - After the initial push, continue to grow the army gradually through spawn events but always ensure all Warriors end up in the Cave for sustained DPS.
  - In the Cave phase, keep Warriors in attack mode and send Farmers back to the Village.

- Why this might improve win chances:
  - Early DPS is crucial to prevent the Dragon from wiping out villagers. A small, early Warrior presence in the Cave increases the chance to bring the Dragon HP down quickly.
  - A conservative, stepwise spawning plan prevents wheat starvation and maintains DPS in the short term while growing the army for the mid-to-late game.
  - By keeping Farmers in Village, wheat production remains steady, enabling ongoing spawning opportunities without collapsing the economy.

Code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Early, small, deterministic push of Warriors into the Cave (up to 3) to start attacking.
        # - Farmers stay in Village (farm) by default, but we spawn conservatively when wheat allows.
        # - Spawns use disjoint donors to keep progression predictable.
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        assigned = set()

        # 1) Early push: move up to 3 Warri ors to the Cave for early DPS
        if len(warriors) >= 3:
            for w in warriors[:3]:
                environment.assign_group(w, "cave")
                assigned.add(w)

        # 2) Default allocations for the rest
        for f in farmers:
            if f not in assigned:
                environment.assign_group(f, "farm")
        for w in warriors:
            if w not in assigned:
                environment.assign_group(w, "cave")
                assigned.add(w)

        # 3) Spawning decisions (conservative and disjoint)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn farmer: at least 4 farmers and wheat >= 10
        if len(farmers) >= 4 and wheat >= 10:
            donors_farm = farmers[:2]  # two farmers become spawn donors
            for d in donors_farm:
                environment.assign_group(d, "spawn farmer")

        # Spawn warrior: use two villagers not used for farmer-spawn, if possible
        remaining_for_war_spawn = [v for v in components if v not in farmers[:2]]
        if len(remaining_for_war_spawn) >= 2 and wheat >= 12:
            donors_war = remaining_for_war_spawn[:2]
            for d in donors_war:
                environment.assign_group(d, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```