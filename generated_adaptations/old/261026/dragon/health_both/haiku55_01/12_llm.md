## Analysis of the previous run

- **The 11.3-step version was the best so far.** Every Farmer and Warrior attacked the Dragon, and the Dragon died in 10 to 12 steps.
- **Damage per step was still too low early on.** Damage was roughly 3 to 6 HP per step, mostly from Warriors, and only two Warrior pairs could be formed each step.
- **Warrior production was capped by the target and the pair limit.** Once the target of 10 was reached, or the per-step limit was hit, extra wheat sat unused.
- **Farmers were a cheap damage source.** Each Farmer that attacks adds 1 damage per step, and the Dragon's counterattack is a per-step roll, so adding attackers adds little extra risk.

## Changes in this version

1. **Faster Warrior production.** Up to three Warrior pairs per step, instead of two, so the Warrior count grows faster while wheat lasts.
2. **Higher Warrior target.** The target rises from 10 to 12 total Warriors, so spending the wheat does not stop early.
3. **Smaller village reserve.** Only one Farmer stays on the farm. The rest either become spawn pairs or join the attack, which gives more early damage.
4. **Farmers attack in the Cave.** Every Farmer that is not spawning goes to "cave" and attacks, as in the previous best version. Warriors attack too.
5. **Spawn pairs are taken before attackers.** Farmers are used for spawning first, so spawning is never starved by Farmers already sent to the Cave.

This is a reasoned adjustment, not a verified result. The simulation should confirm whether the extra early Warriors shorten the average win time.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 12       # total warriors (village + cave) to maintain
    MAX_WARRIOR_PAIRS = 3      # warrior spawn pairs per step
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

        # 2) Spawn warriors from village farmers first (main damage source).
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

        # 3) Keep a minimum number of farmers on the farm.
        reserve = min(self.MIN_VILLAGE_FARMERS, len(available))
        for f in available[:reserve]:
            environment.assign_group(f, "farm")

        # 4) Remaining farmers join the attack (1 damage each per step).
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