## Analysis of the previous run

- **Win rate fell to 33%.** Game 1 and Game 3 stalled at 29 and 40 HP for the rest of the game, so nothing was attacking the Dragon.
- **The stalls came from losing the attackers.** Farmers in the Cave have only 4 HP and take retaliation damage every step, so they died quickly. The Warriors died as well. Once the Cave was empty, nothing was sent back in.
- **Farmers sent to the Cave could not spawn.** Only Village farmers can form spawn pairs, so draining the Village reduced the Warrior production that the fight depended on.
- **Attacking with everyone was too costly.** Keeping Farmers in the Cave while Warriors were alive exposed them to the Dragon's counterattack for little benefit.

## Changes in this version

1. **Warriors are the main attackers.** Every Warrior goes to the Cave and attacks, as before.
2. **Farmers stay in the Village while Warriors are alive.** This keeps the wheat income and the spawn pool intact.
3. **Warrior production is prioritized.** Up to two Warrior pairs are formed per step from Village farmers, while wheat allows and the total Warrior count is below a target.
4. **Farmer reserve for spawning.** A small Farmer pair is spawned when the Farmer count drops, so the population is replenished.
5. **Farmer fallback only when needed.** Farmers join the Cave only when no Warriors are alive in the Village or the Cave. In that case, all Farmers beyond a reserve of two go to attack, so the Dragon is not left unattacked.
6. **Cave phase.** Warriors attack. Farmers in the Cave attack only if no Warriors remain. Otherwise they return to the Village, so they stay alive and keep farming.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 10       # total warriors (village + cave) to maintain
    TARGET_FARMERS = 4         # farmers to keep for wheat and spawning
    MAX_WARRIOR_PAIRS = 2      # warrior spawn pairs per step
    MAX_FARMER_PAIRS = 1       # farmer spawn pairs per step
    FARM_RESERVE = 2           # farmers that always stay in the village

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

        # 2) Spawn warriors first (main damage source).
        warrior_pairs = 0
        while (warrior_pairs < self.MAX_WARRIOR_PAIRS
               and budget >= 12
               and len(available) >= 2
               and total_warriors < self.TARGET_WARRIORS):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            total_warriors += 1
            warrior_pairs += 1

        # 3) Replenish farmers when the population drops.
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

        # 4) Decide whether farmers must fight. Only when no warriors are alive.
        no_warriors = (total_warriors == 0)

        if dragon_hp > 0 and no_warriors and len(available) > self.FARM_RESERVE:
            # Send the surplus farmers to attack; keep a reserve on the farm.
            attackers = available[self.FARM_RESERVE:]
            farmers_on_farm = available[:self.FARM_RESERVE]
            for f in attackers:
                environment.assign_group(f, "cave")
            for f in farmers_on_farm:
                environment.assign_group(f, "farm")
        else:
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
                # Warriors are fighting: farmers go home to survive and farm.
                environment.assign_group(f, "village")
            else:
                # No warriors left: farmers keep the damage going.
                environment.assign_group(f, "attack")
```