# SmartAdaptation for the Dragon Hunt game
#
# Reasoning and updated strategy:
# - Simplify and make the spawning logic robust and deterministic to avoid assignment errors.
# - Use an explicit assigned-by-id map to avoid unhashable-component issues and prevent double assignment.
# - Strategy:
#   * Reserve a small number of farmers to farm each turn (min_farmers_farming).
#   * From the remaining farmers, spawn as many Warriors (pairs, cost 12 wheat) as possible.
#   * Then from the remaining unassigned farmers spawn as many Farmers (pairs, cost 10 wheat) as possible.
#   * Assign all unassigned farmers to "farm".
#   * From Warriors in the Village, send up to attack_squad_size to "cave"; assign others to "farm" to keep them safe and productive.
# - In the Cave:
#   * Farmers return to Village immediately.
#   * Allow up to attack_squad_size Warriors to "attack"; send others back to "village".
#
# This design ensures every component is assigned exactly once per call, avoids unhashable set usage,
# and produces both new warriors and farmers over the course of the game.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attack_squad_size = 3
        self.min_farmers_farming = 1

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        wheat = getattr(environment.farm, "wheat", 0)

        # Assigned tracking by component id to avoid hashability issues
        assigned = {}

        # Reserve some farmers to farm (if possible)
        reserve_count = min(self.min_farmers_farming, len(farmers))
        reserved_farmers = farmers[:reserve_count]
        remaining_farmers = farmers[reserve_count:]

        # Spawn warriors from remaining_farmers in pairs (12 wheat per pair)
        max_warrior_pairs_by_farmers = len(remaining_farmers) // 2
        max_warrior_pairs_by_wheat = wheat // 12
        warrior_pairs = min(max_warrior_pairs_by_farmers, max_warrior_pairs_by_wheat)

        idx = 0
        for _ in range(warrior_pairs):
            f1 = remaining_farmers[idx]
            f2 = remaining_farmers[idx + 1]
            environment.assign_group(f1, "spawn warrior")
            environment.assign_group(f2, "spawn warrior")
            assigned[id(f1)] = True
            assigned[id(f2)] = True
            idx += 2
            wheat -= 12

        # Remaining unassigned farmers after warrior spawns
        remaining_after_war = [f for f in remaining_farmers if id(f) not in assigned]

        # Spawn farmers from remaining_after_war in pairs (10 wheat per pair)
        max_farmer_pairs_by_farmers = len(remaining_after_war) // 2
        max_farmer_pairs_by_wheat = wheat // 10
        farmer_pairs = min(max_farmer_pairs_by_farmers, max_farmer_pairs_by_wheat)

        idx = 0
        for _ in range(farmer_pairs):
            f1 = remaining_after_war[idx]
            f2 = remaining_after_war[idx + 1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            assigned[id(f1)] = True
            assigned[id(f2)] = True
            idx += 2
            wheat -= 10

        # Assign any farmers not used for spawning (including reserved ones) to "farm"
        for f in farmers:
            if id(f) not in assigned:
                environment.assign_group(f, "farm")

        # Assign warriors: send up to attack_squad_size to cave, keep others farming in village
        if warriors:
            sorted_w = sorted(warriors, key=lambda c: getattr(c, "hp", 0), reverse=True)
            to_send = sorted_w[: self.attack_squad_size]
            to_keep = sorted_w[self.attack_squad_size :]
            for w in to_send:
                environment.assign_group(w, "cave")
            for w in to_keep:
                environment.assign_group(w, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Partition by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Send farmers back to village immediately
        for f in farmers:
            environment.assign_group(f, "village")

        # Warriors: allow up to attack_squad_size to attack, send others back to village
        if warriors:
            sorted_w = sorted(warriors, key=lambda c: getattr(c, "hp", 0), reverse=True)
            attackers = sorted_w[: self.attack_squad_size]
            others = sorted_w[self.attack_squad_size :]
            for w in attackers:
                environment.assign_group(w, "attack")
            for w in others:
                environment.assign_group(w, "village")