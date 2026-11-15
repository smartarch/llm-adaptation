

## Analysis and Strategy Improvement

The v4 strategy (20.0 steps) has these inefficiencies:
1. **Warriors leave cave at scm≥5** giving only 4 attacks/cycle — they could attack at scm=5 too (starvation only applies when can't attack, but they can still transit while starving)
2. **Spawning is too conservative** — only 1 pair spawns per step when we could assign 4 farmers to produce 2 warriors at once
3. **Farmers stay in village too long** — in the critical endgame phase, even 1-2 damage per farmer helps close out the fight
4. **Insufficient initial wheat buildup** — need to farm hard for 2-3 steps before any spawning to get a warrior out by step 4-5

**v5 Strategy:**
- **5 attacks per warrior cycle** (scm 1→5 in cave, leave at scm≥6, transit while starving costing 1-2 HP) — 25% more DPS per warrior
- **Batch spawning**: assign 4 farmers to "spawn warrior" when wheat ≥ 24 for 2 warriors per step
- **Aggressive continuous spawning** from step 3 onward
- **Endgame all-in** at HP ≤ 12: all villagers (including farmers) rush cave
- **Tight warrior-to-cave entry**: eat → immediately next step go to cave (arrive scm=1, attack at 1,2,3,4,5)

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
        for w in warriors:
            if dragon_hp <= 12:
                # Endgame: go to cave ASAP unless will starve immediately
                if w.steps_since_meal >= 5:
                    environment.assign_group(w, "eat")
                else:
                    environment.assign_group(w, "cave")
            elif w.steps_since_meal >= 2:
                # Eat to reset scm, so we arrive at cave fresh (scm=1)
                # and get 5 full attack steps (scm 1-5)
                environment.assign_group(w, "eat")
            else:
                # scm 0 or 1: go to cave immediately
                # arrive at scm 1 or 2, still get 4+ attacks
                environment.assign_group(w, "cave")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        available_farmers = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # --- Spawning logic ---
        spawn_pool = available_farmers[:]  # farmers available for actions

        if dragon_hp <= 12:
            # Endgame: no more spawning, all rush cave
            for f in spawn_pool:
                if f.steps_since_meal <= 2:
                    environment.assign_group(f, "cave")
                else:
                    environment.assign_group(f, "eat")
            available_farmers = []
        elif wheat >= 24 and len(spawn_pool) >= 4 and step >= 4:
            # Batch spawn: 4 farmers → 2 warriors
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            environment.assign_group(spawn_pool[2], "spawn warrior")
            environment.assign_group(spawn_pool[3], "spawn warrior")
            available_farmers = spawn_pool[4:]
        elif wheat >= 12 and len(spawn_pool) >= 2 and step >= 3:
            # Single warrior spawn every step
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            available_farmers = spawn_pool[2:]
        elif wheat >= 10 and len(spawn_pool) >= 2 and step <= 2:
            # Very early: one farmer spawn to boost economy
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            available_farmers = spawn_pool[2:]
        else:
            available_farmers = spawn_pool

        # Remaining farmers farm
        for f in available_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if dragon_hp <= 6:
                # Absolute endgame: everyone attacks no matter what
                environment.assign_group(c, "attack")
            elif c.role == "Warrior":
                if c.steps_since_meal >= 6:
                    # Starving - can't attack, must leave
                    environment.assign_group(c, "village")
                else:
                    # Attack at scm 0-5 (5 attacks possible in a fresh cycle)
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                if dragon_hp <= 12:
                    # Endgame: farmers help
                    if c.steps_since_meal >= 5:
                        environment.assign_group(c, "village")
                    else:
                        environment.assign_group(c, "attack")
                else:
                    # Farmers not useful in cave during normal play
                    environment.assign_group(c, "village")
```