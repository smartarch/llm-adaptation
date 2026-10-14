## Analysis of the previous run

- **Win rate is 100%, but the average is 15 steps.** Damage is roughly 3 per step in the early turns, then drops to 0 or 1 per step in several turns (Game 1 stalls at 35 for two steps, Game 3 stalls at 44 and then grinds down at 3 per step).
- **The stalls come from too few Warriors in the Cave.** Warriors are spawned only one pair per step and only up to a target of 6 total, so the early damage rate stays low. Warriors that die or get pulled back also leave gaps.
- **Spawning is slow when wheat is plentiful.** The previous version spent at most one pair per type per step, even when the farm had enough wheat for more.

## Changes in this version

1. **Faster Warrior production.** Up to two Warrior spawn pairs per step while wheat ≥ 12 and enough Farmers are available. Warriors are the main damage source (3 per step each), so the Dragon dies sooner once more of them are present.
2. **Higher Warrior target.** The target rises from 6 to 8 total Warriors, so the Cave stays saturated for the whole fight.
3. **Farmer spawning after Warriors.** At most one Farmer pair per step, and only when Farmers are below a small target and wheat is left over. This keeps wheat income going without starving Warrior production.
4. **Cave-phase logic unchanged in spirit.** Warriors attack every step. Farmers in the Cave return to the Village while Warriors are present, and attack only when no Warriors remain, so the Village is not emptied while Warriors are fighting.
5. **Pending-spawn accounting.** The target check counts spawns already queued this step, so the strategy does not over-assign.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 8       # total warriors (village + cave) we aim to keep
    TARGET_FARMERS = 5        # total farmers we aim to keep
    MAX_WARRIOR_PAIRS = 2     # warrior spawn pairs per step
    MAX_FARMER_PAIRS = 1      # farmer spawn pairs per step

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0
        self.cave_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        total_warriors = len(warriors) + self.cave_warriors
        total_farmers = len(farmers) + self.cave_farmers

        available = list(farmers)
        budget = wheat

        # 2) Spend wheat on warriors first (up to MAX_WARRIOR_PAIRS per step).
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1      # count the pending spawn
            warrior_pairs += 1

        # 3) Then grow the farmer population for wheat income (limited per step).
        farmer_pairs = 0
        while (farmer_pairs < self.MAX_FARMER_PAIRS
               and budget >= 10
               and len(available) >= 2
               and total_farmers < self.TARGET_FARMERS):
            environment.assign_group(available.pop(0), "spawn farmer")
            environment.assign_group(available.pop(0), "spawn farmer")
            budget -= 10
            total_farmers += 1
            farmer_pairs += 1

        # 4) Fallback: if no warriors remain at all, farmers join the fight.
        #    Otherwise everyone left keeps farming.
        if dragon_hp > 0 and total_warriors == 0 and len(available) > 2:
            n_attackers = max(1, (len(available) - 2) // 2)
            for _ in range(n_attackers):
                environment.assign_group(available.pop(0), "cave")

        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        self.cave_warriors = len(warriors)
        self.cave_farmers = len(farmers)

        for w in warriors:
            environment.assign_group(w, "attack")

        for f in farmers:
            if warriors:
                # Warriors are fighting, so farmers return to the village.
                environment.assign_group(f, "village")
            else:
                # No warriors left: farmers keep the damage up.
                environment.assign_group(f, "attack")
```