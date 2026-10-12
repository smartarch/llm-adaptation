Reasoning and updated adaptation strategy

Goal recap:
- Warriors must go to the Cave and attack the Dragon.
- Farmers stay in the Village to farm and/or spawn new villagers.
- Spawning costs: 2 villagers + 10 wheat for a Farmer, or 2 villagers + 12 wheat for a Warrior.
- The Dragon can retaliate when attacked (40% chance to damage every villager in the Cave by 1, 20% chance to eat one random villager in the Cave). If all villagers die, you lose.
- We want to win faster, with a robust plan that scales up DPS while limiting casualties.

What we changed and why:
- Wave-based attack in the Cave: Instead of sending all Warriors at once, send a small, controlled attack wave each step. This reduces the expected casualties from retaliation and keeps more villagers alive for farming and spawning.
- Step- and HP-aware spawning: We gate spawning with a simple “step budget” and adjust aggressiveness based on Dragon HP. Early steps emphasize farming to accumulate wheat; later steps increase spawning to grow DPS more quickly. We also slightly throttle spawns when the Dragon HP is very high to avoid premature overextension.
- Spawn Farmers first: Farmers grow wheat income, enabling more spawns later. Only then spawn Warriors if wheat and farmers allow.
- Ensure Farmers in Cave go back to Village: The strategy consistently moves Farmers back to the Village, focusing on wheat production and spawning rather than staying in the Cave without purpose.

High-level plan:
- Village:
  - Move a small wave of Warriors to the Cave (attack) each step (1 initially, 2 later).
  - Use a step- and HP-aware budget to spawn Farmers first, then Warriors, with a max of 0/1/2 spawns per step depending on step and HP.
  - Remaining Farmers stay in Village to farm.
- Cave:
  - Attack with a wave of Warriors (size determined by Dragon HP and current Warrior count in Cave).
  - Any remaining Warriors in Cave stay in Cave (as reserve) to be deployed in later steps.
  - Farmers in Cave move back to Village.

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
        - cave: Go to Cave (attack in the next step, via a wave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        village_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        wave = 1
        if step >= 8:
            wave = 2
        if step >= 12:
            wave = 2
        wave = min(wave, len(village_warriors))
        to_attack_now = village_warriors[:wave]

        for w in to_attack_now:
            environment.assign_group(w, "cave")

        # Remaining warriors (if any) will stay in village this step (to be moved in future steps)
        remaining_warriors = village_warriors[wave:]

        # Wheat and dragon HP influence spawning budget
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        # Step-based spawn budget
        # Conservative early, ramp up later
        if step < 3:
            max_spawns = 0
        elif step < 6:
            max_spawns = 1
        else:
            max_spawns = 2

        # HP gating
        if dragon_hp > 40:
            max_spawns = max(0, max_spawns - 1)  # be conservative
        elif dragon_hp < 25:
            max_spawns = min(2, max_spawns + 1)  # allow a bit more aggression

        # Compute spawns
        F = len(farmers)
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_farmers = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_farmers // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        spawn_farmer_assignees = farmers[:n_sf]
        spawn_warrior_assignees = farmers[n_sf:n_sf + n_sw]
        farm_assignees = farmers[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are no farmers, the warriors already moved to cave above.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (wave)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        # Collect roles in cave
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        dragon_hp = int(getattr(environment.dragon, "hp", 0))
        total_warriors_in_cave = len(warriors)

        # Determine attack wave size based on dragon HP
        if total_warriors_in_cave <= 0:
            wave_size = 0
        elif dragon_hp > 40:
            wave_size = 1
        elif dragon_hp > 25:
            wave_size = min(2, total_warriors_in_cave)
        else:
            wave_size = min(3, total_warriors_in_cave)

        # Assign attack wave
        attack_candidates = warriors[:wave_size]
        remaining_in_cave = warriors[wave_size:]

        for c in attack_candidates:
            environment.assign_group(c, "attack")
        for c in remaining_in_cave:
            environment.assign_group(c, "cave")

        # Farmers in cave should head back to the Village
        for f in farmers:
            environment.assign_group(f, "village")
```