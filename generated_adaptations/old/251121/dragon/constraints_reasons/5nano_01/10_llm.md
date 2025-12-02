Reasoning and adaptation strategy update

What changed and why:
- The previous implementations risked per-step assignment errors by mutating components multiple times or reassigning in separate loops. To guarantee that every component is assigned exactly once per step, we now build a single explicit mapping (component -> target group) for each phase and then apply it in one pass.
- Scheduling of spawns is made more robust and goal-oriented:
  - Try to spawn as many farmer-pairs as possible to boost wheat production, but also explicitly try to spawn at least one warrior-pair when resources allow. This helps ensure we meet the objective of having new warriors and increasing DPS early.
  - If it's not possible to spawn any warrior this step, we fall back to maximum farmer spawns and preserve farming for wheat production.
- In the cave, we strictly assign each warrior to attack to maximize DPS, and farmers go back to the village. Unknown roles default to safe groups as before.
- This approach eliminates assignment duplication, increases the likelihood of spawning both farmers and warriors early, and keeps the constraints intact.

Code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_village = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All warriors should go to the Cave
        for w in warriors_in_village:
            environment.assign_group(w, "cave")

        f_count = len(farmers)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Build a robust spawn plan with explicit mapping (one assignment per component)
        mapping = {}

        # 1) Determine spawns: try to maximize farmer-spawns first, then ensure at least one warrior-spawn if possible
        max_sf_possible = min(f_count // 2, wheat // 10)
        s_farm_spawns = max_sf_possible
        s_war_spawns = 0

        # Try to find a configuration that includes at least one warrior spawn if resources allow
        best_sf = 0
        best_sw = 0
        best_total_pairs = -1
        # Try all possible farmer-spawn counts to see if we can fit at least one warrior-spawn
        for sf in range(0, max_sf_possible + 1):
            wheat_after = wheat - 10 * sf
            rem_farmers = f_count - 2 * sf
            sw = min(rem_farmers // 2, wheat_after // 12)
            total_pairs = sf + sw
            if sw > 0:
                if total_pairs > best_total_pairs:
                    best_total_pairs = total_pairs
                    best_sf = sf
                    best_sw = sw

        if best_sw > 0:
            s_farm_spawns = best_sf
            s_war_spawns = best_sw
        else:
            # No warrior spawns possible with current resources; use max farmer spawns
            s_farm_spawns = max_sf_possible
            s_war_spawns = 0

        # Build the precise per-component mapping
        idx = 0
        # Spawn farmer group: 2 farmers per farmer-spawn
        for _ in range(s_farm_spawns * 2):
            if idx < f_count:
                mapping[farmers[idx]] = "spawn farmer"
                idx += 1

        # Spawn warrior group: 2 farmers per warrior-spawn
        for _ in range(s_war_spawns * 2):
            if idx < f_count:
                mapping[farmers[idx]] = "spawn warrior"
                idx += 1

        # Remaining farmers go to farming in village
        for j in range(idx, f_count):
            mapping[farmers[j]] = "farm"

        # Non-farmer/unknown components in village: default to farming
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                mapping[c] = "farm"

        # Apply the mapping (one assignment per component)
        for c, grp in mapping.items():
            environment.assign_group(c, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Classify villagers in the Cave
        farmers_in_cave = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Farmers should go to the Village
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # Warriors: maximize DPS by attacking with all warriors
        for w in warriors_in_cave:
            environment.assign_group(w, "attack")

        # Unknown-role villagers: default to cave
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "cave")
```