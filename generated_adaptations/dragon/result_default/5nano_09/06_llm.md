Reasoning and updated adaptation strategy

Goal recap:
- Warriors must go to the Cave and attack the Dragon.
- Farmers should stay in the Village to farm and/or spawn new villagers.
- Spawning costs: 2 villagers + 10 wheat for a Farmer, or 2 villagers + 12 wheat for a Warrior.
- You want to kill the Dragon quickly while managing the Dragon’s potential retaliation in the Cave.

What was suboptimal before:
- Spawns were chosen purely based on current wheat and farmer counts, with no explicit pacing. This could waste wheat early on or underbuild the army at critical times.
- Farmers in the Cave were allowed to stay in Cave in some cases, which is against the preferred long-term strategy (Farmers should stay in the Village for farming/spawning).

Key improvements in this strategy:
- Step-aware spawning: introduce pacing so we build up wheat and population gradually rather than spending aggressively early or delaying growth too long.
  - Steps 0-3: focus on farming (no spawns) to accumulate wheat.
  - Steps 4-6: allow up to 1 spawn per step (if feasible).
  - Steps 7+: allow up to 2 spawns per step (to accelerate growth).
- Spawn prioritization: always spawn Farmers first (to boost wheat production), then use remaining resources to spawn Warriors if there are enough Farmers and wheat.
- In-cave behavior: keep all Warriors in the Cave to attack; move Farmers back to the Village (to farm or spawn) as early as possible.
- This approach aims to build a steady, scalable DPS while maintaining wheat income, increasing the chance to kill the Dragon within the target window.

Code implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Step-based spawning budget
        if step < 4:
            max_spawns = 0
        elif step < 7:
            max_spawns = 1
        else:
            max_spawns = 2

        # Compute how many spawns we can support this step
        # Each spawn requires 2 farmers and a Wheat cost (10 for Farmer, 12 for Warrior)
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_farmers = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_farmers // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        # Assign farmers to groups
        spawn_farmer_assignees = farmers[:n_sf]
        spawn_warrior_assignees = farmers[n_sf:n_sf + n_sw]
        farm_assignees = farmers[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are no farmers, Warriors have already been sent to cave above.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors attack
                environment.assign_group(c, "attack")
            else:
                # Farmers should move back to Village to farm or spawn
                environment.assign_group(c, "village")
```