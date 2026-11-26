

# Adaptation Strategy: Dragon Hunt

## Strategy Overview

The strategy operates in two phases:

**Phase 1 - Buildup (Steps 1-~8):** Aggressively spawn warriors while farmers produce wheat. Everyone eats as needed. Warriors farm in this phase since the Dragon doesn't regenerate until first attacked.

**Phase 2 - Attack (Once ~10+ warriors ready):** Warriors enter a rotation cycle through the Cave: travel → attack (2-3 steps) → travel back → eat. The cycle is ~6-7 steps per warrior, giving each warrior 2-3 attacks per cycle. By staggering warriors based on their `steps_since_meal`, we maintain continuous attacks (critical, since Dragon regenerates 5 HP/step if not attacked).

**Key Rules:**
- Villagers with `steps_since_meal >= 4` must eat (accounting for 1-step travel)
- Cave warriors with `steps_since_meal >= 4` return to village
- Farmers stay in village farming to sustain wheat production
- We ensure at least some warrior is always attacking once combat begins

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

        # Decide when to start attacking: once we have enough warriors and wheat
        if not self.attack_started:
            if step >= 6 and num_warriors >= 10 and wheat >= 25:
                self.attack_started = True

        # Track who has been assigned (use index to avoid id issues)
        assigned = [False] * len(components)

        # Priority 1: Feed villagers who need to eat (steps_since_meal >= 4)
        for i, c in enumerate(components):
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                assigned[i] = True

        if self.attack_started:
            # --- ATTACK PHASE ROTATION ---

            # Priority 2: Warriors that are well-fed go to cave to attack
            # Only send if they can get at least 1 attack before needing to return
            # steps_since_meal 0→arrive(1)+attack(2)+attack(3)+attack(4)+leave(5) = 3 attacks
            # steps_since_meal 1→arrive(2)+attack(3)+attack(4)+leave(5) = 2 attacks
            # steps_since_meal 2→arrive(3)+attack(4)+leave(5) = 1 attack
            for i, c in enumerate(components):
                if not assigned[i] and c.role == "Warrior" and c.steps_since_meal <= 1:
                    environment.assign_group(c, "cave")
                    assigned[i] = True

            # Priority 3: If attack is happening but nobody is in cave and nobody heading there,
            # send a warrior desperately (even at cost of starvation)
            total_in_cave = warriors_in_cave
            heading_to_cave = sum(1 for i, c in enumerate(components) if assigned[i] and not components[i].role == "Farmer")
            if total_in_cave == 0 and not heading_to_cave:
                for i, c in enumerate(components):
                    if not assigned[i] and c.role == "Warrior":
                        environment.assign_group(c, "cave")
                        assigned[i] = True
                        break

            # Remaining villagers: farmers farm, warriors rest/farm in village
            for i, c in enumerate(components):
                if not assigned[i]:
                    environment.assign_group(c, "farm")
                    assigned[i] = True
        else:
            # --- BUILDUP PHASE ---
            unassigned_indices = [i for i in range(len(components)) if not assigned[i]]

            # Spawn warriors aggressively (need pairs of villagers + 12 wheat)
            warriors_to_spawn = max(0, 14 - num_warriors)
            for _ in range(warriors_to_spawn):
                # Find 2 unassigned villagers
                pair = [i for i in unassigned_indices if not assigned[i]][:2]
                if len(pair) >= 2 and wheat >= 12:
                    environment.assign_group(components[pair[0]], "spawn warrior")
                    environment.assign_group(components[pair[1]], "spawn warrior")
                    assigned[pair[0]] = True
                    assigned[pair[1]] = True
                    unassigned_indices.remove(pair[0])
                    unassigned_indices.remove(pair[1])
                    wheat -= 12
                    num_warriors += 1
                else:
                    break

            # Spawn farmers if we have too few (need pairs + 10 wheat)
            farmers_to_spawn = max(0, 5 - num_farmers)
            for _ in range(farmers_to_spawn):
                pair = [i for i in unassigned_indices if not assigned[i]][:2]
                if len(pair) >= 2 and wheat >= 10:
                    environment.assign_group(components[pair[0]], "spawn farmer")
                    environment.assign_group(components[pair[1]], "spawn farmer")
                    assigned[pair[0]] = True
                    assigned[pair[1]] = True
                    unassigned_indices.remove(pair[0])
                    unassigned_indices.remove(pair[1])
                    wheat -= 10
                    num_farmers += 1
                else:
                    break

            # Everyone else farms
            for i in unassigned_indices:
                if not assigned[i]:
                    environment.assign_group(components[i], "farm")
                    assigned[i] = True

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # If steps_since_meal >= 4, must return to village to eat
            # (travel takes 1 step, arriving at 5, then eat resets to 0)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                # Attack the Dragon every other step
                environment.assign_group(c, "attack")
```