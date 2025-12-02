# Adaptive strategy aimed at reducing the number of turns to defeat the Dragon
# Rationale (embedded as comments):
# - Keep all Warriors in the Cave (attack) to maximize early DPS.
# - Use Farmers to drive Wheat production so we can spawn more villagers over time.
# - Dynamically balance spawns based on Dragon HP and current Wheat stock:
#     - When the Dragon is strong (high HP), favor Farmers to accelerate Wheat accumulation and future spawning.
#     - When the Dragon is weakened (low HP), start spawning more Warriors to boost DPS and finish sooner.
# - Cap aggressive spawns to avoid overloading the Cave with non-combatants early, which would increase risk from the Dragon's back-attacks.
# - Always move Warriors to the Cave for attack; Farmers should return to Village if not spawning this turn.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move all Warriors to the Cave (they will attack)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Wheat available at the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Dragon HP to guide spawns
        dragon_hp = getattr(getattr(environment, "dragon", None), "hp", 0)

        # Maximum possible Farmer spawns this step (2 farmers per spawn, 10 wheat per spawn)
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Dynamic cap for Farmer spawns based on Dragon HP
        if dragon_hp > 40:
            sF = min(max_farm_spawns, 2)      # conservative early farming
        elif dragon_hp > 20:
            sF = min(max_farm_spawns, 4)      # moderate farming
        else:
            sF = max_farm_spawns              # aggressive farming when Dragon is weak

        spawn_farmers = farmers[:2 * sF]
        remaining_farmers = farmers[2 * sF:]

        # Wheat remaining after Farmer spawns
        wheat_rem_after_farm = wheat - 10 * sF

        # Determine Warrior spawns from remaining farmers
        sW = 0
        if len(remaining_farmers) >= 2 and wheat_rem_after_farm >= 12:
            # Dynamic Warrior spawn cap guided by Dragon HP
            if dragon_hp > 40:
                cap = 0  # avoid spawning Warriors when Dragon is very strong
            elif dragon_hp > 20:
                cap = 2
            elif dragon_hp > 10:
                cap = 3
            else:
                cap = 5

            sW = min(len(remaining_farmers) // 2, cap, wheat_rem_after_farm // 12)

        spawn_warriors = remaining_farmers[:2 * sW]
        remaining_farmers_after = remaining_farmers[2 * sW:]

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in remaining_farmers_after:
            environment.assign_group(c, "farm")

        # Note: Warriors are already in the cave; non-spawning Farmers keep farming this turn.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack; Farmers return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")