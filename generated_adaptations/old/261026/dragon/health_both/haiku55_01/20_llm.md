## Analysis of the previous run

- **The stall persists despite the cache reset.** The Dragon's HP flattens at 19 or 24 while the game runs to the 30-step limit, so the Cave is empty or idle for most of the fight.
- **Cached state is the weak point.** The strategy tracks `cave_warriors` and `cave_farmers` across phases. When the Cave empties, the cave phase stops running and the counts go stale. Each fix so far patched one stale path and left others open.
- **The reserve logic adds another failure mode.** Holding Farmers back on the farm, or requiring extra Farmers before spawning, can leave a single idle Farmer when the Warriors die.

## Changes in this version

1. **No cached counts.** The village phase decides only from the components it can see right now, so it cannot act on a stale value.
2. **Every Farmer not spawning attacks.** Each village step, every Farmer that is not in a spawn pair goes to the Cave. Farmers in the Cave attack every step, so the Dragon is always attacked while Villagers remain.
3. **Spawn pairs keep at least one attacker.** A pair is formed only when at least three Farmers are in the Village, so one Farmer always remains to attack.
4. **Warrior spawn count tracked by a simple total.** A counter of spawn orders issued, not a live population count, caps Warrior production at 8 orders. This is not stale because it only increases.
5. **Attack structure unchanged.** Warriors go to the Cave, and every villager in the Cave attacks each step.

This is a reasoned change, not a verified result. The simulation should confirm whether the stalls are gone and whether the average win time drops.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    MAX_WARRIOR_SPAWN_ORDERS = 8   # total warrior spawn pairs ever issued
    MAX_WARRIOR_PAIRS = 2          # warrior spawn pairs per step
    MIN_FARMERS_TO_SPAWN = 3       # keep at least one farmer free to attack

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_orders = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior in the village goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn warriors from farmers, keeping at least one farmer free.
        available = list(farmers)
        budget = wheat
        pairs = 0
        while (pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= self.MIN_FARMERS_TO_SPAWN
               and self.warrior_spawn_orders < self.MAX_WARRIOR_SPAWN_ORDERS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            pairs += 1
            self.warrior_spawn_orders += 1

        # 3) Every remaining farmer attacks: 1 damage each per step.
        for f in available:
            environment.assign_group(f, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Everyone in the cave attacks. Retaliation is per step, not per attacker,
        # so extra attackers add damage without adding risk.
        for c in components:
            environment.assign_group(c, "attack")
```