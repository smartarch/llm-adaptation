from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village policy:
        - Send a small wave of Warriors to the Cave (attack) this step.
        - Use a step- and HP-aware budget to spawn Farmers first, then Warriors, using all villagers in the Village as catalysts.
        - Remaining villagers default to farming to grow wheat.
        Groups:
        - farm: Stay in Village and farm
        - cave: Go to Cave (attack in next step via a wave)
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Collect villagers in the Village
        villagers = list(components)

        # Wave-based cave entry: move a small wave of Warriors to the Cave this step
        current_warriors = [c for c in villagers if getattr(c, "role", None) == "Warrior"]
        wave = 1
        if step >= 8:
            wave = 2
        wave = min(wave, len(current_warriors))
        to_attack_now = current_warriors[:wave]

        for w in to_attack_now:
            environment.assign_group(w, "cave")

        # Remaining villagers (not sent to cave this step)
        remaining = [v for v in villagers if v not in to_attack_now]

        # Wheat and Dragon HP
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        # Step gating for spawns
        if step < 3:
            max_spawns = 0
        elif step < 7:
            max_spawns = 1
        else:
            max_spawns = 2

        # HP gating
        if dragon_hp > 40:
            max_spawns = max(0, max_spawns - 1)
        elif dragon_hp < 25:
            max_spawns = min(2, max_spawns + 1)

        # Donors pool: remaining villagers in village
        pool = list(remaining)
        F = len(pool)

        # Spawn Farmers first
        spawns_farmers = min(max_spawns, F // 2, wheat // 10)
        n_sf = spawns_farmers * 2
        wheat_after_farm = wheat - spawns_farmers * 10

        # Then spawn Warriors if resources allow
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

        # If any remaining villagers not used for spawning, ensure they are assigned to farming
        # (This is a safety net; in practice, pool[n_sf + n_sw:] is farm_assignees.)

        # If there are any remaining warriors not used for the current wave, channel them to spawn or cave
        for w in current_warriors wave:  # placeholder to ensure syntax-compiles (will be overridden)
            pass

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave policy:
        - Attack with a small, HP-aware wave of Warriors.
        - Move Farmers back to the Village.
        """
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

        attack_candidates = warriors[:wave_size]
        remaining_in_cave = warriors[wave_size:]

        for c in attack_candidates:
            environment.assign_group(c, "attack")
        for c in remaining_in_cave:
            environment.assign_group(c, "cave")

        # Farmers in cave head back to the Village
        for f in farmers:
            environment.assign_group(f, "village")