## Analysis of the previous run

- **The 33% win rate is the same stall as before.** In Games 1 and 3 the Dragon's HP stopped at 29 and 40, so nothing was attacking for the rest of the game.
- **The guard I added made it worse.** Requiring three Farmers in the Village before spawning meant that once the Warriors died, a single remaining Farmer was kept on the farm, could not spawn, and could not attack.
- **The root cause is an empty Cave.** Once no Warriors remain, the only possible attackers are Farmers in the Village, and the reserve logic kept them out of the fight.

## Changes in this version

1. **No farm reserve when no Warriors are alive.** If the Warrior count is zero, the reserve drops to zero. Every remaining Farmer either spawns or attacks, so the Cave is never left empty while the Dragon lives.
2. **Reserve kept only while Warriors fight.** With Warriors alive, one Farmer still stays on the farm for wheat income.
3. **Spawn requirement matches the reserve.** Spawning needs two Farmers plus the current reserve, so a spawn never leaves the Village with fewer workers than the plan requires.
4. **Same attack structure otherwise.** Warriors go to the Cave, and every villager in the Cave attacks each step.

This is a reasoned fix for the observed stall, not a verified result. The simulation should confirm whether the Cave now stays occupied until the Dragon dies.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 10       # total warriors (village + cave) to maintain
    MAX_WARRIOR_PAIRS = 2      # warrior spawn pairs per step
    MIN_VILLAGE_FARMERS = 1    # farmers kept on the farm while warriors are alive

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

        # Keep a farm reserve only while warriors are alive to fight.
        reserve_needed = self.MIN_VILLAGE_FARMERS if total_warriors > 0 else 0

        # 2) Spawn warriors from village farmers, respecting the reserve.
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2 + reserve_needed
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1      # count the pending spawn
            warrior_pairs += 1

        # 3) Keep the reserve on the farm (only if warriors are alive).
        reserve = min(reserve_needed, len(available))
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