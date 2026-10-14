## Analysis of the previous run

- **Games 1 and 2** lost roughly 3 HP per step, which suggests only one or two Warriors were attacking. The Dragon was killed in 8 to 10 steps.
- **Game 3** stalled at 14 HP from step 10 onward. The Warriors had died, and nothing was attacking the Dragon for the remaining 19 steps. Farmers never entered the Cave, so the strategy had no fallback damage source.
- The spawn cap of 3 events per type was too restrictive. Once it was reached, no new Warriors were produced even while wheat was plentiful.

## Changes in this version

1. **Uncapped, wheat-driven spawning.** Each step, at most one pair is sent to "spawn warrior" when wheat ≥ 12 and the Warrior count is below a target. A pair goes to "spawn farmer" early, when the Farmer count is low, to build wheat income. Both pairs are reassigned every step, so they stay in their spawn groups only while they are meant to.
2. **Farmer fallback attackers.** When no Warriors are in the Cave (and none are about to arrive), up to half of the available Farmers are sent to the "cave" group. Each Farmer adds 1 damage per step, so the Dragon can still be finished after the Warriors fall.
3. **Cave-phase role logic.** Warriors always attack. Farmers attack only when no Warriors are present in the Cave; otherwise they return to the Village.
4. **State tracking.** The number of Warriors in the Cave is recorded during the cave phase, so the village phase can decide whether to send Farmers.

Farmers never enter the Cave while Warriors are alive, so the Village is never emptied. Farmers in the Cave can die, but the Village always keeps at least one farmer to keep the game going.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 6      # total warriors we want to maintain
    TARGET_FARMERS = 6       # total farmers we want to maintain early on
    MIN_FARMERS_IN_VILLAGE = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0   # warriors in cave, observed in last cave phase
        self.cave_farmers = 0    # farmers in cave, observed in last cave phase

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Estimate total population for targets.
        total_warriors = len(warriors) + self.cave_warriors
        total_farmers = len(farmers) + self.cave_farmers

        # 2) If no warriors are (or will be) fighting, send farmers to attack.
        no_warriors_fighting = (total_warriors == 0)
        available = list(farmers)
        if dragon_hp > 0 and no_warriors_fighting:
            # Keep a minimum number of farmers in the village for farming/spawning.
            n_attackers = max(0, len(available) - self.MIN_FARMERS_IN_VILLAGE)
            n_attackers = min(n_attackers, max(1, len(available) // 2))
            for _ in range(n_attackers):
                environment.assign_group(available.pop(0), "cave")

        budget = wheat

        # 3) Spawn at most one pair per type per step, reassigned each step.
        #    Early on, grow the farmer population for wheat income.
        spawned_warrior = False
        spawned_farmer = False

        if (total_farmers < self.TARGET_FARMERS
                and budget >= 10 and len(available) >= 2):
            environment.assign_group(available.pop(0), "spawn farmer")
            environment.assign_group(available.pop(0), "spawn farmer")
            budget -= 10
            spawned_farmer = True

        if (total_warriors < self.TARGET_WARRIORS
                and budget >= 12 and len(available) >= 2):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            spawned_warrior = True

        # 4) Everyone else farms.
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
                # Warriors are present, so farmers return to the village.
                environment.assign_group(f, "village")
            else:
                # No warriors left: farmers keep the damage up.
                environment.assign_group(f, "attack")
```