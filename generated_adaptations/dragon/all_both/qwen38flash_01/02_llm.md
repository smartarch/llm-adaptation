

Looking at this problem, I need to design a strategy that:
1. Gets warriors attacking early (within 15 steps)
2. Staggered warrior rotations to avoid >2 step gaps (dragon regen)
3. Manages eating (every 6 steps, warriors before steps≥3 when going to cave)
4. Spawns enough warriors and farmers for sustainability
5. Keeps farmers producing wheat

**Strategy Design:**

- **Warrior cycling:** Warriors in cave attack while `steps_since_meal < 4`, then go to village to eat. In village, warriors with `steps_since_meal ≥ 3` must eat (can't go to cave). This creates a natural 6-step cycle: 3 attacks + 1 go back + 1 eat + 1 go forward.
- **Staggering:** Early game sends only 1 warrior per step to create offset. A third warrior (spawned) bridges the gaps when the first two go to eat.
- **Spawning:** Spawn warriors in early-mid game for attack power, spawn farmers to ensure wheat economy.
- **Farmers:** Always stay in village, farm to produce wheat, eat when forced (steps≥5).
- **Cave:** Attack unless about to starve (steps≥4), then return to village.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dragon_attacked = False

    def assign_in_village(self, components, environment, group_ids, step):
        # Track whether dragon has been hit (hp < 100)
        if environment.dragon.hp < 100:
            self.dragon_attacked = True

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]
        wheat = environment.farm.wheat

        # --- Handle Warriors in Village ---
        warriors_eat = []   # must eat (forced or blocked)
        warriors_can_go = []  # can go to cave

        for w in warriors:
            if w.steps_since_meal >= 5:
                warriors_eat.append(w)  # FORCED to eat
            elif w.steps_since_meal >= 3:
                warriors_eat.append(w)  # too hungry to go to cave
            else:
                warriors_can_go.append(w)

        # Stagger: early game, send limited warriors to create phase offset
        to_send = []
        to_stay = []

        if warriors_can_go:
            if step <= 2:
                # Very early: send at most 1 warrior per step for stagger
                to_send = warriors_can_go[:1]
                to_stay = warriors_can_go[1:]
            elif step <= 5:
                # Early-mid: send at most half
                send_count = max(1, len(warriors_can_go) // 2)
                to_send = warriors_can_go[:send_count]
                to_stay = warriors_can_go[send_count:]
            else:
                # Later: send all available warriors (natural cycle staggers them)
                to_send = warriors_can_go

        for w in warriors_eat:
            environment.assign_group(w, "eat")
        for w in to_send:
            environment.assign_group(w, "cave")
        for w in to_stay:
            # Warriors staying: eat to reset timer (creates future offset), or farm briefly
            if w.steps_since_meal >= 2:
                environment.assign_group(w, "eat")
            else:
                environment.assign_group(w, "farm")

        # --- Handle Farmers in Village ---
        farmers_eat = []
        farmers_work = []

        for f in farmers:
            if f.steps_since_meal >= 5:
                farmers_eat.append(f)  # FORCED to eat
            else:
                farmers_work.append(f)

        for f in farmers_eat:
            environment.assign_group(f, "eat")

        # --- Spawning Logic ---
        # Prioritize warrior spawns early (need attackers), farmer spawns mid (need wheat)
        # Use pairs of farmers for spawn groups
        
        # Spawn warriors: steps 1-10, need 12 wheat and 2 farmers
        if step >= 1 and step <= 10 and len(farmers_work) >= 2 and wheat >= 12:
            for f in farmers_work[:2]:
                environment.assign_group(f, "spawn warrior")
            farmers_work = farmers_work[2:]
            wheat -= 12

        # Spawn farmers: steps 3-14, need 10 wheat and 2 farmers
        if step >= 3 and step <= 14 and len(farmers_work) >= 2 and wheat >= 10:
            for f in farmers_work[:2]:
                environment.assign_group(f, "spawn farmer")
            farmers_work = farmers_work[2:]
            wheat -= 10

        # Remaining farmers work on the farm
        for f in farmers_work:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.steps_since_meal >= 4:
                # Must return to village to eat before starving (eat at step 5)
                environment.assign_group(c, "village")
            else:
                # Attack the Dragon
                environment.assign_group(c, "attack")
```