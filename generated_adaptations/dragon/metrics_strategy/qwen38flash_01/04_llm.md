

## Strategy Improvements

After analyzing the 21.3 step result, I identified several bottlenecks:
1. **Warriors were returning to eat too early** (at scm=3-4), wasting attack opportunities
2. **Spawning was too conservative** - not spawning fast enough early on
3. **Farmers weren't contributing to late-game damage**
4. **Warriors were being sent back at scm>=4 but could safely attack at scm=5** (starvation is at scm=6)

**New approach:**
- Warriors stay in cave until scm=5 (attack one extra turn), transit back at scm=6 (accept 1 HP loss per cycle)
- Aggressive warrior spawning from step 2 onward (every time 12+ wheat available)
- Endgame mode at Dragon HP ≤ 25: ALL villagers (farmers included) eat then rush to cave
- Warriors in village at scm ≤ 3 are sent to cave (arrives scm=4, attacks at 4,5, then returns)
- Minimize any villager standing idle - always productive

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        # Priority: eat if starving risk, else send to cave ASAP
        warriors_eating = []
        warriors_to_cave = []
        for w in warriors:
            if w.steps_since_meal >= 5:
                # Must eat now (scm=5, if they wait another step they hit 6 = starvation)
                warriors_eating.append(w)
            elif w.steps_since_meal >= 4:
                # scm=4: eat to be safe (arriving at cave would be scm=5, only 1 attack)
                warriors_eating.append(w)
            elif dragon_hp <= 20:
                # Endgame: eat quickly then go back to fight
                if w.steps_since_meal <= 1:
                    warriors_to_cave.append(w)
                else:
                    warriors_eating.append(w)
            elif w.steps_since_meal <= 3:
                # Safe: arrive cave scm<=4, can attack at 4 and 5 (2 attacks minimum)
                warriors_to_cave.append(w)
            else:
                # scm=4 handled above; this shouldn't be reached
                warriors_eating.append(w)

        for w in warriors_eating:
            environment.assign_group(w, "eat")
        for w in warriors_to_cave:
            environment.assign_group(w, "cave")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        available_farmers = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # --- Spawn logic: aggressively spawn warriors ---
        can_spawn_w = wheat >= 12 and len(available_farmers) >= 2
        can_spawn_f = wheat >= 10 and len(available_farmers) >= 2

        spawned = False

        # Always spawn warriors when possible, especially early-mid game
        if step <= 12 and can_spawn_w:
            environment.assign_group(available_farmers[0], "spawn warrior")
            environment.assign_group(available_farmers[1], "spawn warrior")
            available_farmers = available_farmers[2:]
            spawned = True
        elif step <= 16 and can_spawn_w and wheat >= 14:
            # Still spawning warriors mid-game if wheat allows
            environment.assign_group(available_farmers[0], "spawn warrior")
            environment.assign_group(available_farmers[1], "spawn warrior")
            available_farmers = available_farmers[2:]
            spawned = True
        elif step <= 6 and can_spawn_f and not can_spawn_w:
            # Early: spawn a farmer if we can't afford warrior yet
            environment.assign_group(available_farmers[0], "spawn farmer")
            environment.assign_group(available_farmers[1], "spawn farmer")
            available_farmers = available_farmers[2:]
            spawned = True

        # --- Endgame: send farmers to cave to attack ---
        if dragon_hp <= 25 and len(available_farmers) >= 1:
            # Eat then send to cave for final push
            for f in available_farmers:
                if f.steps_since_meal <= 1:
                    environment.assign_group(f, "cave")
                elif f.steps_since_meal <= 3:
                    environment.assign_group(f, "cave")
                else:
                    environment.assign_group(f, "eat")
            available_farmers = []

        # --- Remaining farmers farm ---
        for f in available_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if dragon_hp <= 8:
                # Absolute finish: everyone attacks, ignore hunger
                environment.assign_group(c, "attack")
            elif dragon_hp <= 20:
                # Endgame: warriors attack until scm=6 (starve), farmers attack too
                if c.steps_since_meal >= 6:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            elif c.role == "Warrior":
                if c.steps_since_meal >= 6:
                    # Starving - must leave (lose 1 HP during transit)
                    environment.assign_group(c, "village")
                elif c.steps_since_meal >= 5:
                    # Last safe attack! Attack then leave next step
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers in cave (rare) - useful only in endgame
                if c.steps_since_meal >= 5:
                    environment.assign_group(c, "village")
                elif dragon_hp <= 30:
                    environment.assign_group(c, "attack")
                else:
                    # Go back to farm - more valuable producing wheat
                    environment.assign_group(c, "village")
```

**Key changes from v1 → v2:**
1. Warriors now attack at scm=5 (one extra attack per cycle) and leave at scm=6 (accept 1 HP/cycle loss)
2. Warriors in village at scm=3 are sent to cave (arrive scm=4, attack at 4 and 5)
3. Aggressive warrior spawning from step 0-12 with wheat≥12 (no additional wheat buffer)
4. Endgame at Dragon HP≤20: warriors attack until scm=6 (not scm≥5) for max DPS
5. Dragon HP≤25 triggers farmers to go to cave after eating
6. Dragon HP≤8: everything attacks regardless (game will end in 2-3 steps)