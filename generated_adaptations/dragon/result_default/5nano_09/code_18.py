from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village policy:
        - Send a small wave of Warriors to the Cave (attack) this step.
        - Use a step- and HP-aware budget to spawn Farmers first, then Warriors, using only villagers in the Village as catalysts.
        - Remaining villagers default to farming to grow wheat.
        Groups:
        - farm: Stay in Village and farm
        - cave: Go to Cave (attack in next step via a wave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        village_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        wave = 1
        if step >= 6:
            wave = 2
        wave = min(wave, len(village_warriors))
        to_attack_now = village_warriors[:wave]

        for w in to_attack_now:
            environment.assign_group(w, "cave")

        # Remaining warriors in village (if any) will be handled for spawning or future waves
        remaining_warriors = village_warriors[wave:]

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

        # Compute spawns (use villagers in village as catalysts; we prefer farmers as catalysts)
        pool = [c for c in farmers]  # catalysts we can confidently use for spawns
        F = len(pool)

        # Spawn Farmers first (requires 2 catalysts and 10 wheat)
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        # Remaining catalysts for potential Warrior spawns
        remaining_pool = F - n_sf
        spawns_warriors = min(max_spawns - spawns_farmers, remaining_pool // 2, wheat_after_farm // 12)
        n_sw = spawns_warriors * 2

        # Assign villagers to groups
        spawn_farmer_assignees = pool[:n_sf]
        spawn_warrior_assignees = pool[n_sf:n_sf + n_sw]
        farm_assignees = pool[n_sf + n_sw:]

        for c in spawn_farmer_assignees:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_assignees:
            environment.assign_group(c, "spawn warrior")
        for c in farm_assignees:
            environment.assign_group(c, "farm")

        # If there are remaining Warriors not used for current wave, assign them to future-use path
        for w in remaining_warriors:
            # If we still have wheat to spare and spawns are possible, queue them for spawning;
            # otherwise, keep them in cave as a reserve by assigning them to "cave".
            if wheat > 12 and len(farmers) >= 2:
                environment.assign_group(w, "spawn warrior")
            else:
                environment.assign_group(w, "cave")

        # If there are any farmers not used in spawning, they would naturally be assigned to 'farm' above.
        # This ensures every component gets an assignment.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave policy:
        - Attack with a small, HP-aware wave of Warriors.
        - Move Farmers back to the Village.
        - Remaining Warriors stay in the Cave as reserve for future waves.
        """
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

        # Farmers in cave head back to the Village
        for f in farmers:
            environment.assign_group(f, "village")