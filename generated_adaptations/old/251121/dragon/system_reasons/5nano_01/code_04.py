from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _compute_spawns(self, step, dragon_hp, F, wheat):
        """
        Compute how many new Farmers and Warriors to spawn this step.
        Rules (balanced and adaptive):
        - We spawn at most a small number to avoid starving farming.
        - Prefer to spawn up to 3 Farmers per step if resources allow.
        - Then spawn up to 3 Warriors per step with remaining resources.
        - Spawns are bounded by wheat and by available Farmers (2 farmers per new unit).
        - We adapt caps based on step and dragon HP to aggressively spawn early when urgency is high.
        """
        if F < 2 or wheat < 10:
            return 0, 0

        # Dynamic caps: more aggressive early, taper later
        if step < 6:
            cap_farm = 3
            cap_war = 3
        elif step < 12:
            cap_farm = 2
            cap_war = 2
        else:
            cap_farm = 1
            cap_war = 2  # still allow some war spawns later if resources permit

        # First, try to spawn Farmers
        max_farm_spawns = min(F // 2, wheat // 10, cap_farm)

        # Update resources after potential farmer spawns
        wheat_after_farm = wheat - max_farm_spawns * 10
        remaining_farmers = F - max_farm_spawns * 2

        # Then try to spawn Warriors with remaining resources
        max_war_spawns = min(remaining_farmers // 2, wheat_after_farm // 12, cap_war)

        # Optional: guard against extremely aggressive bursts when dragon HP is very low
        # If dragon HP is low and we already have enough warriors, reduce spawns a bit
        if dragon_hp is not None and dragon_hp <= 10:
            max_farm_spawns = max(0, max_farm_spawns - 1)
            max_war_spawns = max(0, max_war_spawns - 1)

        return max_farm_spawns, max_war_spawns

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Move all Warriors to the cave (group "cave").
        - Farmers stay in village by default (group "farm"), but we may spawn a few new Farmers and Warriors
          using "spawn farmer" and "spawn warrior" groups, to grow the population.
        - The rest of Farmers remain in the "farm" group.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Dragon HP (for adaptive spawning)
        dragon_hp = getattr(environment.dragon, "hp", None)

        # Compute spawn plan
        spawn_farm_n, spawn_war_n = self._compute_spawns(step, dragon_hp, len(farmers), wheat)

        # Indexes for selecting villagers to spawn groups
        # Warriors all go to cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Mark which farmers are assigned to spawn groups
        to_spawn_farm = farmers[:2 * spawn_farm_n] if spawn_farm_n > 0 else []
        to_spawn_war = farmers[2 * spawn_farm_n: 2 * spawn_farm_n + 2 * spawn_war_n] if spawn_war_n > 0 else []

        used_for_spawns = set(to_spawn_farm) | set(to_spawn_war)

        for c in to_spawn_farm:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_war:
            environment.assign_group(c, "spawn warrior")

        # Remaining farmers go to farming
        for c in farmers:
            if c in used_for_spawns:
                continue
            environment.assign_group(c, "farm")

        # Non-farmer components (if any) should stay in village by default
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors attack the Dragon: assign to "attack".
        - Farmers go back to the Village: assign to "village".
        """
        for v in components:
            role = getattr(v, "role", None)
            if role == "Warrior":
                environment.assign_group(v, "attack")
            else:
                # Farmers (and any others) go to Village
                environment.assign_group(v, "village")