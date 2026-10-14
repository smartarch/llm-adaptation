

# Improved Strategy: Aggressive Warrior Production

## Diagnosis of 33% win rate

Re-examining the previous code, I found a critical bug: the spawn counters were set incorrectly:
```python
self.spawned_warriors = self.TARGET_WARRIORS if assign_warrior_pairs > 0 else self.spawned_warriors
```
This **immediately capped** warrior spawning to the target after the first pair, so we typically only spawned 1-2 warriors total. Combined with dragon counterattacks killing warriors, we couldn't sustain enough damage output.

## New Strategy

1. **Proper state tracking**: Track spawned units by actually incrementing counters each time a spawn pair is assigned. Don't use broken heuristics.
2. **Aggressive warrior spawning**: Spawn a warrior every step whenever we have ≥12 wheat and ≥4 farmers remaining (so wheat production doesn't collapse). Only stop when we hit diminishing returns.
3. **Minimal farmer spawning**: Spawn just enough farmers to meet the "at least 2" requirement and to keep wheat production stable (only if farmers drop below 4).
4. **Immediate cave deployment**: Warriors go to "cave" the instant they appear in village; all cave warriors attack every step.
5. **Keep all spare farmers farming** to fuel continued warrior production.

Economics: each warrior costs 12 wheat = 3 steps of one farmer pair's output, but yields 3 dmg/step forever. With enough farmers farming in parallel, warrior spawning compounds quickly into overwhelming damage.

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Aggressive warrior-production strategy.
    - All warriors rush the cave and attack every step.
    - Farmers farm; pairs are allocated to warrior-spawning first (cheapest
      damage upgrade), then to farmer-spawning only when farmers run low.
    - Properly tracks spawn counts to keep producing warriors continuously.
    """

    # Hard requirements from the task
    MIN_SPAWNED_WARRIORS = 2
    MIN_SPAWNED_FARMERS = 2
    # We want at least this many farmers alive so wheat keeps flowing.
    MIN_FARMERS_KEEP = 4
    # How many total warriors we aim to accumulate attacking the dragon.
    TARGET_TOTAL_WARRIORS = 8

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initial_counted = False
        self._initial_warriors = 0
        self._initial_farmers = 0
        self.spawned_warriors = 0  # warriors we caused to be spawned
        self.spawned_farmers = 0   # farmers we caused to be spawned

    def _count_initial(self, components):
        if not self._initial_counted:
            self._initial_warriors = sum(1 for c in components if c.role == "Warrior")
            self._initial_farmers = sum(1 for c in components if c.role == "Farmer")
            self._initial_counted = True

    # ------------------------------------------------------------------ #
    def assign_in_village(self, components, environment, group_ids, step: int):
        self._count_initial(components)

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior instantly goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        # Sort: pair up healthier farmers for spawning.
        farmers_sorted = sorted(farmers, key=lambda c: -c.hp)
        n = len(farmers_sorted)
        pairs_total = n // 2

        wheat = environment.farm.wheat

        total_farmers = self._initial_farmers + self.spawned_farmers
        total_warriors = self._initial_warriors + self.spawned_warriors

        warrior_pairs = 0
        farmer_pairs = 0
        remaining_wheat = wheat

        # 1) First, ensure the required 2 farmers get spawned (task req)
        #    and that we don't run out of wheat production.
        #    Only spend on farmer spawns if we'd otherwise be below MIN_FARMERS_KEEP
        #    or we haven't met the minimum spawn requirement.
        need_farmer_spawns = (self.spawned_farmers < self.MIN_SPAWNED_FARMERS)
        low_farmers = (total_farmers < self.MIN_FARMERS_KEEP + 2)  # +2 to account for the pair being consumed

        if (need_farmer_spawns or low_farmers) and pairs_total >= 1 and remaining_wheat >= 10:
            farmer_pairs = 1
            remaining_wheat -= 10

        # 2) Now spend the rest on warrior spawning, as long as we keep
        #    enough farmers farming (we already reserved them via pairing logic).
        #    We can afford warrior_pairs if after consuming 2*farmer_pairs farmers,
        #    the remaining farmers are enough to keep producing.
        pairs_left = pairs_total - farmer_pairs
        while (warrior_pairs < pairs_left
               and remaining_wheat >= 12
               and (total_warriors + warrior_pairs) < self.TARGET_TOTAL_WARRIORS):
            warrior_pairs += 1
            remaining_wheat -= 12

        # 3) If we still have spare pairs and wheat and haven't met minimum
        #    warrior spawns yet, push harder.
        while (self.spawned_warriors + warrior_pairs < self.MIN_SPAWNED_WARRIORS
               and warrior_pairs < pairs_left
               and remaining_wheat >= 12):
            warrior_pairs += 1
            remaining_wheat -= 12

        # Assign warrior pairs first.
        idx = 0
        for _ in range(warrior_pairs):
            environment.assign_group(farmers_sorted[idx], "spawn warrior")
            environment.assign_group(farmers_sorted[idx + 1], "spawn warrior")
            idx += 2
        self.spawned_warriors += warrior_pairs

        # Then farmer pairs.
        for _ in range(farmer_pairs):
            environment.assign_group(farmers_sorted[idx], "spawn farmer")
            environment.assign_group(farmers_sorted[idx + 1], "spawn farmer")
            idx += 2
        self.spawned_farmers += farmer_pairs

        # Everyone else farms.
        while idx < n:
            environment.assign_group(farmers_sorted[idx], "farm")
            idx += 1

    # ------------------------------------------------------------------ #
    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Stray farmer: send back to farm.
                environment.assign_group(c, "village")
            else:
                # Warriors (and any other combatant) attack relentlessly.
                environment.assign_group(c, "attack")
```