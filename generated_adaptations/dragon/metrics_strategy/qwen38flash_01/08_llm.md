

## Revised Strategy Analysis

After three failed attempts, I realize the core issues:
1. **Attacking too early kills warriors** before they can build up enough damage output
2. **Spawning conditions were too strict** - I required too many farmers before spawning
3. **Key insight: warriors can STAY in the cave without attacking** - the Dragon only counter-attacks when attacked, so we can safely accumulate warriors in the cave, then launch a coordinated assault

**New Plan:**
- Farmers farm to accumulate wheat, spawn warriors aggressively (need only 2 farmers in spawn group + wheat, keep remaining farmers farming)
- Warriors go to cave in **STAY** mode (no attack, no back-damage) until we have ≥5 warriors accumulated
- Once ≥5 warriors are in cave OR step ≥12 (satisfies early attack constraint), ALL warriors attack simultaneously
- 5 warriors × 3 dmg = 15/step → kills 50 HP Dragon in ~4 steps
- Late game (step ≥ 20): send everyone, farmers included
- Weak warriors (HP ≤ 1) in cave get sent back to preserve them

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_accumulated = 0
        self.attack_mode = False
        self.spawned_warriors = 0
        self.MAX_EXTRA_WARRIORS = 6

    def assign_in_village(self, components, environment, group_ids, step: int):
        if not components:
            return

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Emergency: very late or dragon nearly dead — everyone to cave
        if step >= 22 or dragon_hp <= 12:
            for c in components:
                environment.assign_group(c, "cave")
            return

        # All warriors from village go to cave
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        n_f = len(farmers)

        # Spawning: need 2 farmers in spawn group + 1 farmer farming minimum
        # Priority: spawn warriors until we have enough
        if n_f >= 3 and wheat >= 12 and self.spawned_warriors < self.MAX_EXTRA_WARRIORS:
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            self.spawned_warriors += 1
            return

        # Spawn farmers only if we have surplus economy
        if n_f >= 4 and wheat >= 10:
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            return

        # Default: all farmers work the farm
        for f in farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if not components:
            return

        dragon_hp = environment.dragon.hp
        warriors = [c for c in components if c.role == "Warrior"]
        self.warriors_accumulated = len(warriors)

        # Decide whether to start the attack phase
        # Trigger attack when: enough warriors built up, or forced by time
        should_attack = (
            self.warriors_accumulated >= 5
            or step >= 12
            or self.attack_mode
            or dragon_hp <= 10
        )

        if self.warriors_accumulated >= 5:
            self.attack_mode = True

        if should_attack:
            # All warriors attack the dragon
            for c in components:
                if c.role == "Warrior":
                    environment.assign_group(c, "attack")
                else:
                    # Farmers deal only 1 dmg; send back to village unless truly late
                    if step >= 20:
                        environment.assign_group(c, "attack")
                    else:
                        environment.assign_group(c, "village")
        else:
            # Build-up phase: warriors stay in cave (no back-damage), farmers go back
            for c in components:
                if c.role == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "village")
```