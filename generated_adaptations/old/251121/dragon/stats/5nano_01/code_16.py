from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Adaptive spawning strategy:
        - Always keep Warriors in the Cave to attack.
        - Farmers stay in the Village and can farm or spawn new villagers.
        - Spawning policy adapts to Dragon HP:
            - High HP (>40): aggressively spawn farmers first, then warriors (up to 2 spawns each).
            - Medium HP (20-40): spawn fewer farmers, and up to 1 warrior spawn.
            - Low HP (<=20): still allow up to 1 warrior spawn if resources permit to finish quickly.
        - Spawns are implemented by moving villagers into "spawn farmer" or "spawn warrior" groups;
          the rest go to "farm".
        """
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Always send Warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat and Dragon HP
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        farm_spawns = 0
        war_spawns = 0

        if wheat >= 10 and len(farmers) >= 2:
            max_farm_spawns = min(len(farmers) // 2, wheat // 10)

            if dragon_hp > 40:
                farm_spawns = min(max_farm_spawns, 2)
            elif dragon_hp > 20:
                farm_spawns = min(max_farm_spawns, 1)
            else:
                # Low HP: allow at most 1 farmer-spawn if any
                farm_spawns = min(max_farm_spawns, 1)

            wheat_after_farm = wheat - farm_spawns * 10
            rem_farmers = len(farmers) - 2 * farm_spawns

            if rem_farmers >= 2 and wheat_after_farm >= 12:
                max_war_spawns = min(rem_farmers // 2, wheat_after_farm // 12)
                if dragon_hp > 40:
                    war_spawns = min(max_war_spawns, 2)
                elif dragon_hp > 20:
                    war_spawns = min(max_war_spawns, 1)
                else:
                    # Low HP: allow at most 1 warrior-spawn if possible to finish quickly
                    war_spawns = min(max_war_spawns, 1)

        spawn_farmer_count = 2 * farm_spawns
        spawn_warrior_count = 2 * war_spawns

        # Assign farmers to the correct groups
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave behavior:
        - All Warriors attack the Dragon.
        - Farmers stay in the Village.
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")