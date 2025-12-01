Reasoning and updated adaptation strategy

Goal recap:
- Warriors must go to the Cave and attack the Dragon.
- Farmers stay in the Village to farm and/or spawn new villagers.
- Spawning costs: 2 villagers + 10 wheat for a Farmer, or 2 villagers + 12 wheat for a Warrior.
- Dragon can retaliate in the Cave (40% chance deal 1 damage to every villager there; 20% chance to eat one random villager in the Cave). If all villagers die, you lose.
- Aim: reduce the number of turns to kill the Dragon, while keeping enough villagers alive to survive retaliation and sustain wheat production.

What to improve:
- Use live Dragon HP to adapt spawn pacing. If the Dragon is strong (high HP), we should be more conservative with spawns to reduce risk and ensure we build a reliable DPS in the Cave. If the Dragon is weak (low HP), we can be more aggressive to finish quickly.
- Maintain wheat income by prioritizing Farmers for spawning first, since they increase wheat production, enabling future spawns and faster long-term DPS.
- Keep Warriors in the Cave attacking, but avoid overwhelming the Cave with too many villagers at once to limit potential cascading losses from retaliation. Use step-based pacing for spawns and gate them by Wheat and number of Farmers.

Adaptation strategy:
- All Warriors in village are sent to the Cave (attack) as required.
- Farmers stay in the Village to farm or spawn.
- Spawning is paced by step and Dragon HP:
  - Step 0-2: no spawning to stabilize wheat.
  - Step 3-5: at most 1 spawn this step.
  - Step 6+: up to 2 spawns per step (if resources allow).
- Spawn prioritization:
  - Always attempt to spawn Farmers first (requires 2 Farmers and 10 Wheat to create a new Farmer).
  - If Wheat and Farms allow, spawn Warriors next (requires 2 Farmers and 12 Wheat to create a new Warrior).
- Use live Dragon HP to slightly adjust max spawns per step:
  - If Dragon HP > 40, constrain spawns to be more conservative.
  - If Dragon HP < 25, allow a bit more aggressive spawns to finish sooner.
- In Cave, Warriors attack; Farmers in Cave move back to Village.

Code (Python)

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
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        # Step-based base spawns
        if step < 3:
            base_spawns = 0
        elif step < 6:
            base_spawns = 1
        else:
            base_spawns = 2

        # HP-aware adjustment to spawning aggressiveness
        if dragon_hp > 40:
            max_spawns = max(0, base_spawns - 1)  # be conservative
        elif dragon_hp < 25:
            max_spawns = min(2, base_spawns + 1)  # more aggressive when close to death
        else:
            max_spawns = base_spawns

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