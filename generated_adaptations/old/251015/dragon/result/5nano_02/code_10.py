# Improved adaptation strategy (new heuristic to try and win faster)
# Rationale:
# - All Warriors must go to the Cave and contribute to Dragon DPS, but sending too many
#   villagers into the Cave increases the risk from the Dragon's back-attacks.
# - Keep farming village growth as a priority to build wheat income, which enables spawning
#   more villagers over time.
# - Spawn Farmers aggressively early (to boost wheat long-term) but cap early spawns to limit
#   the risk of crowding in the Cave from future Warriors.
# - Only spawn Warriors later (if we have spare wheat and enough farmers to convert) to increase
#   DPS when the situation has stabilized.
# - In the Cave, send Farmers back to the Village to reduce the number of non-combatants in the cave.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers by role currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Move all Warriors to the Cave (per rule: all Warriors attack from the Cave)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Wheat available for spawning decisions
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawn Farmers aggressively early but cap the number to avoid overgrowing the cave with risk.
        # Farmer spawn requires 2 farmers and 10 wheat -> up to min(len(farmers)//2, wheat//10) spawns
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        # Cap early to reduce risk and improve early game balance
        sF = min(max_farm_spawns, 3)

        spawn_farmers = farmers[:2 * sF]
        remaining_farmers = farmers[2 * sF:]

        # After initial farming spawns, consider spawning Warriors only if stepping into a later phase
        sW = 0
        if step >= 4:
            # Warrior spawn requires 2 farmers and 12 wheat
            sW = min(len(remaining_farmers) // 2, (wheat - 10 * sF) // 12, 2)

        spawn_warriors = remaining_farmers[:2 * sW]
        remaining_farmers_after = remaining_farmers[2 * sW:]

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")
        for c in remaining_farmers_after:
            environment.assign_group(c, "farm")

        # If any villagers were neither farmers nor warriors (edge cases), farm by default
        # (not strictly necessary as the above covers all current farmers)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors attack; Farmers return to the Village to continue farming/spawning
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")