# SmartAdaptation for the Dragon Hunt game
#
# Reasoning and updated strategy:
# - Goal: keep winning quickly while "reducing the damage to the fields" — i.e., increase the
#   number of villagers who actually farm across the game so the farm (wheat) is less impacted.
# - Observations:
#   * The Dragon retaliates when attacked; if many villagers are present in the Cave they all
#     suffer when the Dragon uses its area effect. Therefore keeping the absolute number of
#     villagers in the Cave low reduces casualties and preserves villagers that can farm.
#   * Farmers must largely remain in the Village to produce wheat. Spawning consumes pairs of
#     farmers, which temporarily reduces farming. To protect wheat production, always reserve
#     a small group of farmers to keep farming each turn.
#   * Warriors are the damage dealers. Rather than sending all warriors to attack every turn,
#     we use a small attack squad (rotating implicitly) so fewer villagers are exposed in the Cave.
# - Concrete rules implemented:
#   1. Reserve a minimum number of farmers to farm each turn (min_farmers_farming = 2 when possible).
#   2. Use remaining farmers for spawning. Prioritize spawning Warriors (pairs cost 12 wheat) but
#      do so only from the farmers that are not reserved to farm.
#   3. Spawn Farmers (pairs cost 10 wheat) only after warrior spawns are allocated and if wheat remains.
#   4. Limit the number of Warriors attacking in the Cave per turn to attack_squad_size (3).
#      Warriors beyond that are kept in the Village (assigned to farm) to both produce wheat and
#      avoid being exposed to the Dragon's area attacks.
#   5. Farmers found in the Cave are immediately sent back to the Village.
#
# The approach raises the average number of farming villagers and reduces the number of villagers
# exposed to the Cave's area attacks, while still allowing steady spawning of Warriors so the Dragon
# is defeated reliably.
#
# Implementation follows the DragonHuntAdaptation interface and always assigns each component
# explicitly each call.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Maximum number of warriors that attack the dragon in a single step.
        # Keeping this small reduces how many villagers are exposed to cave-area damage.
        self.attack_squad_size = 3
        # Minimum number of farmers we always keep farming if available
        self.min_farmers_farming = 2

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Village into:
          - "farm": stay and farm
          - "cave": go to Cave
          - "spawn farmer": spawn farmer (pairs, cost 10 wheat)
          - "spawn warrior": spawn warrior (pairs, cost 12 wheat)
        Strategy:
          - Reserve min_farmers_farming farmers to "farm" if available.
          - Use remaining farmers in pairs to spawn warriors first (as many as wheat & pairs allow),
            then spawn farmers with leftover pairs & wheat.
          - Send a small number of warriors (up to attack_squad_size) to "cave"; keep other warriors
            farming in the Village to protect the fields and produce wheat.
        """
        # Partition components
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        wheat = getattr(environment.farm, "wheat", 0)

        # Decide how many farmers to keep farming
        reserved_count = min(self.min_farmers_farming, len(farmers))
        reserved_farmers = farmers[:reserved_count]
        remaining_farmers = farmers[reserved_count:]

        # Greedily spawn warriors from remaining farmers (needs 2 farmers and 12 wheat per spawn)
        assigned_set = set()
        pairs_available = len(remaining_farmers) // 2
        max_warrior_spawns_by_wheat = wheat // 12
        warrior_spawns = min(pairs_available, max_warrior_spawns_by_wheat)

        idx = 0
        for _ in range(warrior_spawns):
            f1 = remaining_farmers[idx]; f2 = remaining_farmers[idx+1]
            environment.assign_group(f1, "spawn warrior")
            environment.assign_group(f2, "spawn warrior")
            assigned_set.add(f1); assigned_set.add(f2)
            idx += 2
            wheat -= 12

        # Update remaining farmers after warrior spawn assignments
        remaining_after_war = [f for f in remaining_farmers if f not in assigned_set]

        # Spawn farmers from remaining_after_war if wheat allows (2 farmers and 10 wheat per spawn)
        pairs_available = len(remaining_after_war) // 2
        max_farmer_spawns_by_wheat = wheat // 10
        farmer_spawns = min(pairs_available, max_farmer_spawns_by_wheat)

        idx = 0
        for _ in range(farmer_spawns):
            f1 = remaining_after_war[idx]; f2 = remaining_after_war[idx+1]
            environment.assign_group(f1, "spawn farmer")
            environment.assign_group(f2, "spawn farmer")
            assigned_set.add(f1); assigned_set.add(f2)
            idx += 2
            wheat -= 10

        # Any remaining unassigned farmers go to farm
        for f in farmers:
            if f not in assigned_set:
                environment.assign_group(f, "farm")

        # Decide which warriors to send to cave: send up to attack_squad_size
        # Keep the rest in Village to farm (safe) — they produce 2 wheat when farming.
        # Prefer higher-hp warriors to be in the attack squad for resilience.
        if warriors:
            # sort warriors by hp descending (prefer tougher warriors to attack)
            sorted_w = sorted(warriors, key=lambda c: getattr(c, "hp", 0), reverse=True)
            to_send = sorted_w[: self.attack_squad_size]
            to_keep = sorted_w[self.attack_squad_size :]
            for w in to_send:
                environment.assign_group(w, "cave")
            for w in to_keep:
                # keep safe and productive
                environment.assign_group(w, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Cave into:
          - "attack": attack the Dragon
          - "cave": remain in Cave (we avoid this to reduce exposure)
          - "village": return to Village
        Strategy:
          - Farmers in Cave are immediately sent back to the Village.
          - For Warriors in Cave, allow up to attack_squad_size to "attack" (choose highest HP).
            Send any other Warriors back to the Village to avoid unnecessary exposure.
        """
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        # Send farmers back to village immediately
        for f in farmers:
            environment.assign_group(f, "village")

        if warriors:
            # choose the strongest warriors to attack (more resilient)
            sorted_w = sorted(warriors, key=lambda c: getattr(c, "hp", 0), reverse=True)
            attackers = sorted_w[: self.attack_squad_size]
            others = sorted_w[self.attack_squad_size :]
            for w in attackers:
                environment.assign_group(w, "attack")
            for w in others:
                # return to village to protect them and the fields
                environment.assign_group(w, "village")