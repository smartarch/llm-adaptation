

Looking at the failures, I can identify these issues:

1. **`test_no_invalid_assignments`**: I wasn't accounting for wheat consumed by eating when checking if spawning is affordable. Eating consumes 1 wheat per eater, which must come from the same pool as spawning costs.

2. **`test_all_assigned`**: My pair-spawning logic had a bug where an odd number of remaining villagers would leave one unassigned. The index-based removal from lists was also buggy.

For optimization: I'll send warriors to cave earlier (once we have ~8 warriors), use a rotation stagger, and be more aggressive with spawning.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attack_started = False

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        num_warriors = len(all_warriors)
        num_farmers = len(all_farmers)
        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")

        # Phase 1: Assign eaters (steps_since_meal >= 4 means they need to eat soon)
        eaters = []
        non_eaters = []
        for c in components:
            if c.steps_since_meal >= 4:
                eaters.append(c)
            else:
                non_eaters.append(c)

        for c in eaters:
            environment.assign_group(c, "eat")

        # Calculate available wheat after accounting for eating costs
        eat_cost = len(eaters)  # 1 wheat per eater
        available_wheat = wheat - eat_cost

        # Determine if we should start attacking
        # Need enough warriors to sustain a rotation (at least 6-8)
        if not self.attack_started:
            if num_warriors >= 8 and available_wheat >= 15 and step >= 4:
                self.attack_started = True

        # Phase 2: Spawn warriors aggressively if not yet attacking
        spawn_candidates = []
        other_candidates = []
        for c in non_eaters:
            if not self.attack_started and num_warriors < 16:
                spawn_candidates.append(c)
            else:
                other_candidates.append(c)

        # Spawn warriors in pairs (need 12 wheat each)
        spawned = []
        remaining_spawn = []
        for c in spawn_candidates:
            remaining_spawn.append(c)

        while len(remaining_spawn) >= 2 and available_wheat >= 12 and num_warriors < 16:
            c1 = remaining_spawn.pop(0)
            c2 = remaining_spawn.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            available_wheat -= 12
            num_warriors += 1
            spawned.extend([c1, c2])

        # Add back unspawned candidates to the general pool
        remaining_pool = other_candidates + remaining_spawn

        # Phase 3: Assign remaining villagers
        if self.attack_started:
            # Send warriors to cave for attack rotation
            # Warriors with steps_since_meal <= 2 can afford the trip (arrive at 3, attack 4-5, leave at 5)
            sent_to_cave = 0
            for c in remaining_pool:
                if c.role == "Warrior" and c.steps_since_meal <= 1:
                    environment.assign_group(c, "cave")
                    sent_to_cave += 1
                elif c.role == "Warrior" and c.steps_since_meal <= 2 and warriors_in_cave == 0 and sent_to_cave == 0:
                    # Emergency: send someone if nobody is in cave
                    environment.assign_group(c, "cave")
                    sent_to_cave += 1
                else:
                    environment.assign_group(c, "farm")
        else:
            # Buildup phase: everyone farms (spawned ones are already handled)
            for c in remaining_pool:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # If steps_since_meal >= 4, must return to village to eat
            # (they'll arrive in village at 5, eat next step bringing it to 0, or eat at 5)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```