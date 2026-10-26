

# Improved Strategy Analysis

## Why the previous approach failed (0% win rate)

1. **Too cautious with spawning**: Waiting until step ≥ 3 and requiring too many conditions delayed warrior production.
2. **Sending warriors back to village**: Warriors at HP ≤ 1 were sent back, wasting their attack potential and violating the "keep warriors in cave" spirit.
3. **Not aggressive enough**: We need to maximize warrior count ASAP. The dragon has 50 HP, warriors deal 3 damage. We need ~17 warrior-attacks minimum. With only 1-2 warriors, the dragon's counter-attacks (50% chance all in cave lose 1 HP, 20% chance one gets eaten) will kill them before we win.

## New Strategy

1. **All warriors go to cave immediately and NEVER leave** – they attack every single turn.
2. **Farmers farm aggressively** and spawn warriors as soon as wheat ≥ 12. Sacrifice 2 farmers per warrior spawn – it "pays back" in ~2 turns.
3. **Spawn warriors first, farmers second** – warriors are 3× more valuable.
4. **Spawn aggressively every turn** if wheat allows (can spawn multiple warriors per turn if enough wheat + farmers).
5. **Spawn 2 farmers minimum** to satisfy requirements and sustain wheat production.
6. **Keep all warriors in cave attacking** – even at 1 HP, they deal 3 damage. The expected damage from staying outweighs the risk.

## Code

```python
import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors immediately go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        wheat = environment.farm.wheat
        assigned = set()

        # Spawn warriors aggressively: every turn we have 4+ farmers and 12+ wheat
        # Use exactly 2 farmers per spawn, keep at least 2 farming if possible
        remaining_farmers = list(farmers)

        while len(remaining_farmers) >= 4 and wheat >= 12:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            assigned.add(id(remaining_farmers[0]))
            assigned.add(id(remaining_farmers[1]))
            wheat -= 12
            self.spawned_warriors += 1
            remaining_farmers = remaining_farmers[2:]

        # Spawn farmers: only if we've already got at least 2 warrior spawns
        # and still have surplus farmers
        remaining_farmers = [f for f in farmers if id(f) not in assigned]

        while len(remaining_farmers) >= 4 and wheat >= 10 and self.spawned_warriors >= 2:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            assigned.add(id(remaining_farmers[0]))
            assigned.add(id(remaining_farmers[1]))
            wheat -= 10
            self.spawned_farmers += 1
            remaining_farmers = remaining_farmers[2:]

        # All unassigned farmers go farm
        for f in farmers:
            if id(f) not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # ALL warriors in cave attack the dragon every turn - never retreat
        # Non-warriors (if any) go back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```