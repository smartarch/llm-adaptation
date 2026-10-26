## Analysis of the previous run

- **The 33% win rate came from stalls.** In Games 1 and 3 the Dragon's HP stopped falling at 29 and 40, so nothing was attacking for the rest of the game.
- **The stalls followed the reserve logic.** Warriors were sent into the Cave while Farmers were held back, and Farmers were sent to attack only when no Warriors were alive. Once the Warriors died, the remaining Farmers were either spawning or on the farm, so the Cave stayed empty.
- **The best result so far was the "everyone attacks" version (11.3 steps, 100% win rate).** It never stalled because every non-spawning villager was in the Cave every step.

## Changes in this version

1. **Revert to the all-attack structure.** Warriors and non-spawning Farmers both go to the Cave and attack every step. Retaliation is a per-step roll, so extra attackers add damage without adding risk.
2. **Spawning never takes the last Farmer.** Spawn pairs are formed only while at least one Farmer remains free, so the Village always keeps a worker.
3. **One Farmer always stays on the farm.** This keeps wheat income and guarantees a spawn pool for the next step.
4. **Warrior target of 10 and two pairs per step.** These are the settings from the 11.3-step version. Raising the target to 12 and the pairs to 3 did not improve the result.

This is a reasoned revert with a stall guard, not a verified improvement. The simulation should confirm whether the stall-free behaviour keeps the 100% win rate at about 11 steps.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 10       # total warriors (village + cave) to maintain
    MAX_WARRIOR_PAIRS = 2      # warrior spawn pairs per step
    MIN_VILLAGE_FARMERS = 1    # farmers that always stay on the farm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0
        self.cave_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        total_warriors = len(warriors) + self.cave_warriors
        available = list(farmers)
        budget = wheat

        # 2) Spawn warriors from village farmers, but never take the last
        #    reserved farmer, so the village always keeps a worker.
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2 + self.MIN_VILLAGE_FARMERS
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1      # count the pending spawn
            warrior_pairs += 1

        # 3) Keep a minimum number of farmers on the farm.
        reserve = min(self.MIN_VILLAGE_FARMERS, len(available))
        for f in available[:reserve]:
            environment.assign_group(f, "farm")

        # 4) All remaining farmers join the attack (1 damage each per step).
        for f in available[reserve:]:
            environment.assign_group(f, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        self.cave_warriors = len(warriors)
        self.cave_farmers = len(farmers)

        # Everyone in the cave attacks: retaliation is per step, not per attacker.
        for c in components:
            environment.assign_group(c, "attack")
```