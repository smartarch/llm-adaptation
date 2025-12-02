```py
# New adaptive strategy aimed at reducing the number of turns to kill the Dragon
# Rationale:
# - Keep all Warriors in the Cave to maximize early DPS, but avoid letting the Cave grow out of control.
# - Use Farmers to drive Wheat production, enabling spawning of more villagers (both Farmers and Warriors) over time.
# - Make spawns contingent on the Dragon's current HP:
#     - If the Dragon is still strong (HP > 25), favor Farmer spawns to boost long-term wheat and future spawns.
#     - If the Dragon is weakened (HP <= 25), favor Warrior spawns to boost DPS quickly and finish sooner.
# - Spawn decisions are bounded so we don't overshoot Wheat budgets or overwhelm the Cave with non-combatants.
# - In the Cave, Warriors attack; Farmers always return to the Village.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move all Warriors to the Cave (they will attack)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Wheat available at the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine how many Farmer spawns we can trigger this turn
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Strategic cap: be more aggressive on farmers when dragon is weak, more balanced earlier
        dragon_hp = getattr(getattr(environment, "dragon", None), "hp", 0)
        if dragon_hp > 25:
            sF = min(max_farm_spawns, 4)
        else:
            sF = min(max_farm_spawns, 6)

        spawn_farmers = farmers[:2 * sF]
        remaining_farmers = farmers[2 * sF:]

        # Wheat remaining after Farmer spawns
        wheat_rem_after_farm = wheat - 10 * sF

        # Determine Warrior spawns from remaining farmers
        sW = 0
        if len(remaining_farmers) >= 2 and wheat_rem_after_farm >= 12:
            # Dynamic cap: more aggressive DPS when dragon is weak
            if dragon_hp > 25:
                cap = 3
            else:
                cap = 5  # allow more warriors later when dragon is weaker
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

        # Note: Warriors are in Cave; non-spawning Farmers keep farming

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack the Dragon; Farmers return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```