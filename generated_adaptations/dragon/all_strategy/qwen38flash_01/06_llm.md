

## Strategy Description

The failures revealed:
1. My spawning logic wasn't actually spawning enough new villagers (the while loop conditions were too restrictive, leaving 0 farmers spawned).
2. For the `no_initial_warriors` seed, the dragon wasn't being attacked within 15 steps.
3. The dragon wasn't being killed within 30 steps overall.

**Fixes:**
- Use a cleaner spawn routine that tracks remaining available farmers and correctly increments counters, ensuring at least 2 warriors AND 2 farmers get spawned ("a few" of each).
- Aggressively spawn warriors early (target 4 total) to build attack power, while keeping enough farmers farming for wheat income.
- Always send warriors in village to cave immediately, guaranteeing attack within 15 steps even when no warriors start on the field (a spawned warrior reaches the cave within a few steps).
- In the cave, warriors always attack; farmers in the cave help attack only in emergencies (low dragon HP / running out of time), otherwise they return to the village.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors in village immediately head to cave to attack the dragon.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Remaining farmers pool used for spawning / farming decisions.
        pool = list(farmers)

        def try_spawn(target_group_name, cost):
            nonlocal wheat
            if len(pool) < 2 or wheat < cost:
                return False
            f1 = pool.pop(0)
            f2 = pool.pop(0)
            environment.assign_group(f1, target_group_name)
            environment.assign_group(f2, target_group_name)
            wheat -= cost
            return True

        # Goal: at least a few warriors and at least a few farmers spawned.
        # Spawn warriors first (they are the damage dealers), then farmers.
        # Always leave at least one farmer in the pool to farm for wheat if
        # we still have things to do later.

        # Priority 1: build attack power - up to 4 spawned warriors.
        while self.spawned_warriors < 4:
            # Keep at least 2 farmers for wheat income if possible.
            if len(pool) < 2 or wheat < 12:
                break
            if len(pool) - 2 < 2 and self.spawned_farmers < 2 and wheat < 22:
                # Spawning a warrior now would leave us with too few farmers
                # to sustain wheat production; farm this step instead.
                break
            if try_spawn("spawn warrior", 12):
                self.spawned_warriors += 1
            else:
                break

        # Priority 2: sustain wheat production - up to 2 spawned farmers.
        while self.spawned_farmers < 2:
            if len(pool) < 2 or wheat < 10:
                break
            # Need a farmer remaining after the pair is used for spawning.
            if len(pool) - 2 < 1:
                break
            if try_spawn("spawn farmer", 10):
                self.spawned_farmers += 1
            else:
                break

        # Everyone left in the pool farms.
        for f in pool:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp
        remaining_steps = 30 - step

        warriors_in_cave = [c for c in components if c.role == "Warrior"]
        farmers_in_cave = [c for c in components if c.role == "Farmer"]

        # Warriors always attack while alive - speed beats survival here.
        for w in warriors_in_cave:
            environment.assign_group(w, "attack")

        # Estimate whether we can kill the dragon with warriors alone.
        num_warriors = len(warriors_in_cave)
        warrior_dps = num_warriors * 3
        # Rough estimate of expected warrior deaths per step from dragon attacks
        # (40% chance 1 dmg each + 20% chance one dies) - assume slow attrition.
        projected_dps = max(warrior_dps * 0.7, 1)
        damage_needed = dragon_hp
        projected_kills = projected_dps * max(remaining_steps - 1, 0)

        emergency = (projected_kills < damage_needed) or (remaining_steps <= 5)

        for f in farmers_in_cave:
            if emergency and f.hp > 1:
                # Sacrifice some farming to push the dragon down.
                environment.assign_group(f, "attack")
            else:
                # Otherwise return to the village to farm / spawn.
                environment.assign_group(f, "village")
```