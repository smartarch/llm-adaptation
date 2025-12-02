from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _fast_spawns(self, step, dragon_hp, F, wheat):
        """
        Decide how many new Farmers and Warriors to spawn this step.
        - Spawn Warriors first (up to a cap), then Farmers.
        - Caps adapt with step to be aggressive early and then moderate later.
        - Each Warrior spawn consumes 2 Farmers and 12 wheat.
        - Each Farmer spawn consumes 2 Farmers and 10 wheat.
        Returns (spawn_farm_n, spawn_war_n) as numbers of new Farmers and new Warriors to spawn.
        """
        if F < 2 or wheat < 10:
            return 0, 0

        # Adaptive caps: more aggressive early
        if step <= 4:
            cap_war = 4
            cap_farm = 2
        elif step <= 8:
            cap_war = 3
            cap_farm = 2
        else:
            cap_war = 2
            cap_farm = 2

        # First, try to spawn Warriors
        max_war_spawns = min(cap_war, F // 2, wheat // 12)

        # Resources left after possible Warrior spawns
        wheat_after_war = wheat - max_war_spawns * 12
        remaining_farmers = F - max_war_spawns * 2

        # Then try to spawn Farmers with remaining resources
        max_farm_spawns = min(cap_farm, remaining_farmers // 2, wheat_after_war // 10)

        # Optional micro-adjustment: if dragon HP is very high, push a bit more to War spawns
        if dragon_hp is not None and dragon_hp > 40:
            extra_war = min(1, (remaining_farmers // 2) if remaining_farmers >= 2 else 0)
            extra_war = min(extra_war, (wheat_after_war // 12) if wheat_after_war >= 12 else 0)
            max_war_spawns = max_war_spawns + extra_war
            max_war_spawns = min(max_war_spawns, cap_war, F // 2, wheat // 12)

            # Recompute after extra war spawns
            wheat_after_war = wheat - max_war_spawns * 12
            remaining_farmers = F - max_war_spawns * 2
            max_farm_spawns = min(cap_farm, remaining_farmers // 2, wheat_after_war // 10)

        return max_farm_spawns, max_war_spawns

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Move all Warriors to the cave (group "cave").
        - Use a bounded spawn strategy to create new Farmers and Warriors:
          - Spawn Farmers: 2 Farmers per new Farmer, 10 wheat per new Farmer.
          - Spawn Warriors: 2 Farmers per new Warrior, 12 wheat per new Warrior.
        - Remaining Farmers stay in the Village and farm (group "farm").
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Dragon HP (for potential adaptive spawns)
        dragon_hp = getattr(environment.dragon, "hp", None)

        # Decide spawns
        spawn_farm_n, spawn_war_n = self._fast_spawns(step, dragon_hp, len(farmers), wheat)

        # 1) Warriors go to cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn Farmers grouping
        to_spawn_farm = farmers[:2 * spawn_farm_n] if spawn_farm_n > 0 else []
        to_spawn_war = farmers[2 * spawn_farm_n: 2 * spawn_farm_n + 2 * spawn_war_n] if spawn_war_n > 0 else []

        for c in to_spawn_farm:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_war:
            environment.assign_group(c, "spawn warrior")

        # 3) Remaining Farmers stay in the Village to farm
        used_for_spawns = set(to_spawn_farm) | set(to_spawn_war)
        for c in farmers:
            if c in used_for_spawns:
                continue
            environment.assign_group(c, "farm")

        # Any non-farmer components (if any) go to Village by default
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors attack the Dragon (group "attack").
        - Farmers go back to the Village (group "village").
        """
        for v in components:
            role = getattr(v, "role", None)
            if role == "Warrior":
                environment.assign_group(v, "attack")
            else:
                environment.assign_group(v, "village")