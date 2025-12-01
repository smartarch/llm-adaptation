from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to Cave (attack in the next step, via a controlled wave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # All villagers currently in the Village (Farmers and Warriors)
        villagers = list(components)

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        # Default wave: 1, escalate to 2 in later steps
        wave = 1
        if step >= 6:
            wave = 2
        wave = min(wave, len([v for v in villagers if getattr(v, "role", None) == "Warrior"]))
        to_attack_now = [v for v in villagers if getattr(v, "role", None) == "Warrior"][:wave]

        for w in to_attack_now:
            environment.assign_group(w, "cave")

        # Remaining villagers in village after moving the attack wave
        remaining_in_village = [v for v in villagers if v not in to_attack_now]

        # Wheat and dragon HP influence spawning budget
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        # Step-based spawn budget (conservative early, ramp later)
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

        # Compute spawns (spawns use villagers in village as catalysts)
        pool = remaining_in_village
        F = len(pool)

        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        remaining_pool = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_pool // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        spawn_farmer_assignees = pool[:n_sf]
        spawn_warrior_assignees = pool[n_sf:n_sf + n_sw]
        farm_assignees = pool[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are any remaining villagers in the village not used for spawning or attacking,
        # assign them to farming by default to keep wheat income growing.
        # (In this implementation, all remaining are already assigned above, but this is a safety net.)

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (wave-based)
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        # Roles currently in the Cave
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        dragon_hp = int(getattr(environment.dragon, "hp", 0))
        total_warriors_in_cave = len(warriors)

        # Determine attack wave size based on dragon HP and available warriors
        if total_warriors_in_cave <= 0:
            wave_size = 0
        elif dragon_hp > 40:
            wave_size = 1
        elif dragon_hp > 25:
            wave_size = min(2, total_warriors_in_cave)
        else:
            wave_size = min(3, total_warriors_in_cave)

        attack_candidates = warriors[:wave_size]
        remaining_in_cave = warriors[wave_size:]

        for c in attack_candidates:
            environment.assign_group(c, "attack")
        for c in remaining_in_cave:
            environment.assign_group(c, "cave")

        # Farmers in cave should head back to the Village
        for f in farmers:
            environment.assign_group(f, "village")