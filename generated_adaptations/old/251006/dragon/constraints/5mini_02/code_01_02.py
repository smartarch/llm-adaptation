# Strategy and reasoning:
# 
# Goal recap:
# - Kill the Dragon as quickly as possible.
# - Warriors are the primary damage dealers (3 dmg); Farmers produce wheat (and deal 1 dmg).
# - Spawning requires assigning pairs of villagers to a spawn group and consuming wheat
#   (12 for a warrior, 10 for a farmer). At least two villagers must be assigned to that spawn group
#   for a spawn to occur.
# - All Warriors should go to the Cave and attack. All Farmers should remain in the Village,
#   either farming or participating in spawns to create more villagers (both types are useful).
#
# Key decisions:
# 1. Send every warrior in the Village to the Cave (group "cave") so they can join the fight.
#    In the Cave, all warriors will be assigned to "attack".
# 2. Keep farmers in the Village by default and have them "farm" to accumulate wheat.
# 3. Use farmers in pairs to spawn new Warriors when wheat allows. Warriors accelerate killing,
#    so prioritize spawning warriors whenever there are at least two farmers in the Village and
#    at least 12 wheat per warrior to be spawned.
# 4. If no warrior spawn is possible, optionally spawn additional farmers occasionally to keep
#    population growth (throttled to avoid wasting wheat). This uses the "spawn farmer" group
#    in pairs when wheat >= 10 and every few steps (controlled by step % 3).
# 5. If any Farmers somehow end up in the Cave, immediately send them back to the Village
#    (group "village"). All Warriors in the Cave go to "attack".
#
# Implementation notes:
# - assign_in_village: split components into farmers and warriors. Warriors are sent to "cave".
#   Farmers are either put into spawn groups (in pairs) according to available wheat and policy,
#   or left to "farm".
# - We greedily spawn as many warriors as wheat and farmer pairs allow (assigning 2 farmers per warrior).
#   After allocating for warrior spawns, if there are still unused farmer pairs and the step-based rule
#   triggers, we assign a single farmer-spawn pair to "spawn farmer".
# - assign_in_cave: send all Warriors to "attack", Farmers to "village" (to keep Farmers farming).
#
# The code below implements this strategy in a class SmartAdaptation derived from the provided base.
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # If desired, we could keep some state across steps. For now, policy is stateless
        # except for using the provided step counter for throttling farmer spawns.
        self._last_step = -1

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: list of villagers currently in the Village
        groups available: "farm", "cave", "spawn farmer", "spawn warrior"
        """
        # Validate group names exist (not strictly necessary, but helps catch typos)
        required = {"farm", "cave", "spawn farmer", "spawn warrior"}
        # (If some group is missing, we still proceed but assume names are correct per spec)
        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # 1) Send all warriors in the Village to the Cave to join the fight
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) For farmers: decide which to farm and which to use for spawning
        num_farmers = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many warrior spawns we can afford and have farmer pairs for:
        # Each warrior spawn consumes 12 wheat and requires 2 assigned villagers.
        max_possible_warriors_by_wheat = wheat // 12
        max_possible_warriors_by_pairs = num_farmers // 2
        warrior_spawns = min(max_possible_warriors_by_wheat, max_possible_warriors_by_pairs)

        # We don't want to always spend all wheat on spawns in early steps if it would leave no farmers,
        # but warriors are crucial to kill the dragon quickly. We'll be greedy but limited by farmers.
        assigned = set()

        if warrior_spawns > 0:
            # Assign 2 * warrior_spawns farmers to "spawn warrior"
            to_assign_count = warrior_spawns * 2
            for f in farmers[:to_assign_count]:
                environment.assign_group(f, "spawn warrior")
                assigned.add(f)

        # After warrior spawn allocation, consider spawning additional farmer(s) occasionally
        remaining_farmers = [f for f in farmers if f not in assigned]
        remaining_wheat_after_warriors = wheat - (warrior_spawns * 12)

        # Throttle farmer spawning so we don't endlessly convert wheat to more farmers every step:
        # spawn a farmer pair only every 3rd step (arbitrary heuristic) if wheat permits.
        if len(remaining_farmers) >= 2 and remaining_wheat_after_warriors >= 10:
            if (step % 3) == 0:
                # Assign exactly 2 farmers to spawn a new farmer
                for f in remaining_farmers[:2]:
                    environment.assign_group(f, "spawn farmer")
                    assigned.add(f)

        # Any farmer not assigned to spawn should remain farming
        for f in farmers:
            if f not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: list of villagers currently in the Cave
        groups available: "attack", "cave", "village"
        """
        # Send Warriors to attack, Farmers back to village
        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                # All warriors should go to the Cave and attack the Dragon
                environment.assign_group(c, "attack")
            else:
                # Farmers should not stay in the Cave; send them back to the Village to farm or spawn
                environment.assign_group(c, "village")