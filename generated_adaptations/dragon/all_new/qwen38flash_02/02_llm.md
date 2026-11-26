

# Adaptation Strategy: Dragon Hunt - Rotating Attack Phase

## Strategy Overview

The core idea is a **two-phase approach with warrior rotation**:

1. **Build Phase (early steps):** Prioritize spawning warriors while farmers produce wheat. Keep everyone fed.

2. **Attack Phase (once ≥3 warriors exist):** Warriors rotate in and out of the cave using a staggered cycle (each warrior: eat→travel→attack×3→travel→eat = 6 steps). With 3 warriors offset by 2 steps, we maintain continuous attacks (3 damage/step average = 9 per 6 steps > 5 regen + net 4 HP/step).

3. **Safety Rules:** Any villager with `steps_since_meal ≥ 4` goes back to village to eat. Villagers with `hp ≤ 2` retreat. Farmers always farm unless needed for spawning.

4. **Wheat Management:** At least 2 farmers always farm (10 wheat/step) to sustain eating costs and fund warrior spawns.

```py
import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._attack_started = False

    def assign_in_village(self, components, environment, group_ids, step):
        if not components:
            return

        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        warriors_in_cave = sum(1 for w in environment.warriors if w.location == "Cave")
        total_farmers = len(environment.farmers)
        dragon_hp = environment.dragon.hp

        # Determine attack phase: have enough warriors to sustain rotation
        attack_phase = total_warriors >= 3

        # Categorize villagers
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Assign warriors ---
        warriors_fed = []
        for w in warriors:
            if w.steps_since_meal >= 5:
                # Urgent: must eat now (about to starve)
                environment.assign_group(w, "eat")
            elif w.steps_since_meal >= 4:
                # Go eat soon
                environment.assign_group(w, "eat")
            elif attack_phase and w.hp >= 3:
                # Healthy warrior in attack phase: go to cave
                environment.assign_group(w, "cave")
            elif w.hp <= 2:
                # Too weak, rest in village (farm lightly or eat if needed)
                if w.steps_since_meal >= 3:
                    environment.assign_group(w, "eat")
                else:
                    environment.assign_group(w, "farm")
            else:
                # Not enough warriors yet or no attack phase
                if not attack_phase and wheat >= 12 and len(farmers) >= 2:
                    # Don't spawn yet if we can get warriors from existing pool
                    environment.assign_group(w, "farm")
                else:
                    environment.assign_group(w, "cave")  # send to build up cave presence
                warriors_fed.append(w)

        # --- Assign farmers ---
        # Reserve some farmers for farming to produce wheat
        farmers_fed = []
        spawn_candidates = []
        eat_farmers = []
        farm_farmers = []

        for f in farmers:
            if f.steps_since_meal >= 5:
                environment.assign_group(f, "eat")
            elif f.steps_since_meal >= 4:
                environment.assign_group(f, "eat")
            else:
                farmers_fed.append(f)

        # Among farmers who don't urgently need food:
        # Strategy: 2-3 farm, 2 can spawn warriors if needed
        # Always keep at least 2 farming if possible
        min_farmers_farming = min(2, len(farmers_fed))

        if attack_phase:
            # Farmers stay and farm during attack phase
            for i, f in enumerate(farmers_fed):
                environment.assign_group(f, "farm")
        else:
            # Build phase: try to spawn warriors if we have enough wheat and farmers
            num_farm = len(farmers_fed)
            num_spawn_possible = (num_farm - min_farmers_farming) // 2
            num_spawn = min(num_spawn_possible, 1)  # spawn 1 warrior per step max

            for i, f in enumerate(farmers_fed):
                if i < num_spawn * 2 and wheat >= 12:
                    environment.assign_group(f, "spawn warrior")
                elif i < num_spawn * 2:
                    environment.assign_group(f, "farm")
                else:
                    environment.assign_group(f, "farm")

        # If there are leftover unassigned (shouldn't happen, but safety)
        for f in farmers_fed:
            try:
                # Check if already assigned - in practice, we assigned all above
                pass
            except Exception:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        if not components:
            return

        dragon_hp = environment.dragon.hp

        for c in components:
            if c.steps_since_meal >= 5:
                # About to starve - must go to village immediately
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= 4:
                # Need to leave to eat soon
                environment.assign_group(c, "village")
            elif c.hp <= 2:
                # Too fragile to stay in cave with dragon attacks
                environment.assign_group(c, "village")
            elif dragon_hp <= 3 and c.role == "Farmer":
                # Close to killing dragon - even farmers can finish
                environment.assign_group(c, "attack")
            else:
                # Default: attack the dragon
                environment.assign_group(c, "attack")
```