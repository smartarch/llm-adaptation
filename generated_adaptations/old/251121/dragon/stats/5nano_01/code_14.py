from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Strategy (adaptive, aggressive when beneficial):
        - Always keep Warriors in the Cave to attack; move all Warriors to the Cave now.
        - Farmers stay in the Village and can farm or spawn new villagers (Farmers/Warriors).
        - Spawning policy (adaptive):
            - Compute how many Farmer-spawns we can do this step: 2 Farmers per spawn, 10 Wheat per spawn.
            - Then compute Warrior-spawns with remaining Farmers and Wheat: 2 Warriors per spawn, 12 Wheat per spawn.
            - Adapt aggressiveness by Dragon HP:
                - If Dragon HP is high (> 40): spawn as many Farmer-spawns as possible, then as many Warrior-spawns as possible.
                - If Dragon HP is medium (20-40): reduce Warrior-spawns to a safer level.
                - If Dragon HP is low (<= 20): favor farming and slow down Warrior-spawns to avoid overcommitting attackers in risky steps.
        - Spawns are created by assigning villagers to "spawn farmer" or "spawn warrior" groups; the rest remain in "farm".
        - All Warriors are sent to the Cave in this step (they will attack in the Cave step).
        - This strategy aims to boost DPS early when the dragon is strong, while ensuring wheat is invested to sustain growth.
        """
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Always send Warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Wheat available at the Farm and current Dragon HP
        wheat = int(getattr(environment.farm, "wheat", 0))
        dragon_hp = int(getattr(environment.dragon, "hp", 0))

        farm_spawns = 0
        war_spawns = 0

        # Determine spawns based on resources and dragon strength
        if wheat >= 10 and len(farmers) >= 2:
            max_farm_spawns = min(len(farmers) // 2, wheat // 10)

            if dragon_hp > 40:
                # Aggressive: use all possible farmer-spawns
                farm_spawns = max_farm_spawns
            elif dragon_hp > 20:
                # Moderate: spawn about half of the possible farmer-spawns
                farm_spawns = max_farm_spawns // 2
            else:
                # Low HP: minimize farmer-spawns to conserve wheat for attacking force later
                farm_spawns = 0

            wheat_after_farm = wheat - farm_spawns * 10
            rem_farmers = len(farmers) - 2 * farm_spawns

            # Warrior spawns based on remaining resources
            if rem_farmers >= 2 and wheat_after_farm >= 12:
                max_war_spawns = min(rem_farmers // 2, wheat_after_farm // 12)
                if dragon_hp > 40:
                    war_spawns = max_war_spawns
                elif dragon_hp > 20:
                    war_spawns = max_war_spawns // 2
                else:
                    war_spawns = 0

        spawn_farmer_count = 2 * farm_spawns
        spawn_warrior_count = 2 * war_spawns

        # Assign farmers to correct groups
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")
            elif i < spawn_farmer_count + spawn_warrior_count:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Strategy in the Cave:
        - All Warriors attack the Dragon.
        - Farmers stay in the Village (safe from direct Dragon attack in cave).
        """
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")