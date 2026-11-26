

Looking at this problem, I need to design a strategy that:
1. Builds up warriors quickly to deal maximum damage
2. Maintains eating rotation so no villager starves
3. Staggers warriors' eating cycles to ensure continuous dragon attacks (preventing 5 HP regen)
4. Manages wheat production for spawning and feeding

**Strategy Overview:**
- **Phase 1 (early steps):** Farm wheat and spawn warriors using pairs of farmers
- **Phase 2 (attack phase):** Send warriors to cave in staggered groups to avoid synchronized eating breaks. Warriors in cave attack unless they need to eat (s_m >= 4 → go to village; s_m >= 4 in village → eat)
- **Eating management:** Leave cave at s_m >= 4 (arrive at village with s_m=5, eat next step). In village, eat at s_m >= 4 to be safe.
- **Wheat management:** Keep minimal farmers farming (1-2 farmers produce 5-10 wheat/step, more than enough to feed everyone at ~1 wheat/6 steps/person)

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_sent_count = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Identify villagers that must eat NOW (s_m >= 4)
        must_eat = [c for c in components if c.steps_since_meal >= 4]
        must_eat_ids = set(id(c) for c in must_eat)

        # Assign must_eat villagers to eat group
        for c in must_eat:
            environment.assign_group(c, "eat")

        # Remaining villagers (not in must_eat)
        remaining = [c for c in components if id(c) not in must_eat_ids]

        warriors_remaining = [c for c in remaining if c.role == "Warrior"]
        farmers_remaining = [c for c in remaining if c.role == "Farmer"]

        total_warriors = len(environment.warriors)
        total_villagers = len(environment.warriors) + len(environment.farmers)

        if step <= 4:
            # BUILD PHASE: Spawn warriors and farm wheat
            # Use farmers for spawning warriors (save warriors for combat)
            spawn_candidates = list(farmers_remaining)

            i = 0
            while i + 1 < len(spawn_candidates) and wheat >= 12:
                environment.assign_group(spawn_candidates[i], "spawn warrior")
                environment.assign_group(spawn_candidates[i + 1], "spawn warrior")
                wheat -= 12
                i += 2

            # Remaining farmers farm for wheat
            for c in spawn_candidates[i:]:
                environment.assign_group(c, "farm")

            # Send warriors to cave in staggered groups (1-2 per step early on)
            num_to_send = min(len(warriors_remaining), 2)
            for c in warriors_remaining[:num_to_send]:
                environment.assign_group(c, "cave")
            # Rest stay in village (farm for extra wheat)
            for c in warriors_remaining[num_to_send:]:
                environment.assign_group(c, "farm")

        else:
            # ATTACK PHASE
            # All warriors in village go to cave
            for c in warriors_remaining:
                environment.assign_group(c, "cave")

            # Farmers: need some farming for wheat (eating costs)
            # 1 farmer produces 5w/step; each villager needs ~0.17w/step
            # 1 farmer can sustain many villagers, but keep buffer for safety
            num_farm = min(2, len(farmers_remaining))

            for i, c in enumerate(farmers_remaining):
                if i < num_farm:
                    environment.assign_group(c, "farm")
                elif wheat >= 40:
                    # Excess wheat: send extra farmers to cave for small damage
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 4:
                # Must leave cave to go eat; arriving in village with s_m=5, eat next step
                environment.assign_group(c, "village")
            else:
                # Attack the dragon
                environment.assign_group(c, "attack")
```