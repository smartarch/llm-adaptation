from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Aggressive Warrior-first strategy.

    - Warriors always go to the cave and attack every step.
    - Farmers stay in the village, farm wheat, and spawn new units.
    - Spawn priority: Warriors first (until a healthy pool exists), then a
      couple of Farmers, then farm-only.
    - Instance state guarantees at least 2 Warriors and 2 Farmers are spawned.
    """

    # Minimum spawns required by the task
    REQUIRED_WARRIORS_SPAWNED = 2
    REQUIRED_FARMERS_SPAWNED = 2
    # Target number of spawned warriors before we relax the priority
    TARGET_WARRIORS = 4
    # Target number of spawned farmers before we relax the priority
    TARGET_FARMERS = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Counters of units we have caused to be spawned over the whole game.
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        # Track pairs currently in a spawn group so we don't double count.
        self._pending_warrior_pairs = 0
        self._pending_farmer_pairs = 0

    # ------------------------------------------------------------------ #
    # Village phase
    # ------------------------------------------------------------------ #
    def assign_in_village(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # 1) Every warrior must rush to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Reset pending counters; we recount from the actual assignments below.
        self._pending_warrior_pairs = 0
        self._pending_farmer_pairs = 0

        if not farmers:
            return

        # Sort farmers by HP descending so the healthier pair spawns units.
        farmers_sorted = sorted(farmers, key=lambda c: -c.hp)

        wheat = environment.farm.wheat
        # How many pairs of farmers we can afford right now.
        # We don't know exact current wheat consumption timing, so we
        # greedily decide pair by pair checking affordability.
        remaining_wheat = wheat

        pairs_available = len(farmers_sorted) // 2
        assign_warrior_pairs = 0
        assign_farmer_pairs = 0

        # Decide how many warrior pairs to spawn this step.
        while (self.spawned_warriors + assign_warrior_pairs < self.TARGET_WARRIORS
               and assign_warrior_pairs < pairs_available
               and remaining_wheat >= 12):
            assign_warrior_pairs += 1
            remaining_wheat -= 12

        # Decide how many farmer pairs to spawn this step.
        while (self.spawned_farmers + 2 * assign_farmer_pairs < self.TARGET_FARMERS * 2
               and (assign_warrior_pairs + assign_farmer_pairs) < pairs_available
               and remaining_wheat >= 10):
            assign_farmer_pairs += 1
            remaining_wheat -= 10

        # Assign the chosen pairs.
        idx = 0
        for _ in range(assign_warrior_pairs):
            environment.assign_group(farmers_sorted[idx], "spawn warrior")
            environment.assign_group(farmers_sorted[idx + 1], "spawn warrior")
            idx += 2
            self._pending_warrior_pairs += 1

        for _ in range(assign_farmer_pairs):
            environment.assign_group(farmers_sorted[idx], "spawn farmer")
            environment.assign_group(farmers_sorted[idx + 1], "spawn farmer")
            idx += 2
            self._pending_farmer_pairs += 1

        # Everyone else farms.
        while idx < len(farmers_sorted):
            environment.assign_group(farmers_sorted[idx], "farm")
            idx += 1

        # Estimate spawn counts for the next step (spawned units appear later).
        # We add 2 per spawned pair, as each spawn consumes 2 farmers and
        # yields 1 new unit. We track cumulative spawns heuristically.
        self.spawned_warriors = self.TARGET_WARRIORS if assign_warrior_pairs > 0 \
            else self.spawned_warriors
        self.spawned_farmers = self.TARGET_FARMERS if assign_farmer_pairs > 0 \
            else self.spawned_farmers

    # ------------------------------------------------------------------ #
    # Cave phase
    # ------------------------------------------------------------------ #
    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # Attack every single step the warrior is in the cave.
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers don't belong here; send them back to farm.
                environment.assign_group(c, "village")
            else:
                # Fallback: treat as attacker.
                environment.assign_group(c, "attack")