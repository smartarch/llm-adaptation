

Looking at the failures, I need to fix several issues:

1. **Wheat checking**: Must verify sufficient wheat before assigning to "eat" or "spawn" groups
2. **All components assigned**: Every component must get exactly one group assignment (fallback needed)
3. **Dragon attack continuity**: Need better warrior staggering and cycling to ensure attacks never have >2 step gaps
4. **Forced eating**: Villagers at `steps_since_meal >= 5` must eat, but we need wheat available

**Strategy redesign:**
- Track wheat budget carefully, eating has absolute priority over spawning
- Warriors in cave attack while `steps_since_meal < 3`, then return to village
- In village, warriors with `steps_since_meal >= 3` must eat before going to cave
- Stagger initial warrior deployment to create phase offset for continuous attack coverage
- Spawn a 3rd warrior early to guarantee continuous attack coverage (2-attack cycle with 3-step gap needs 3 warriors)
- Farmers stay in village, only forced to eat at `steps_since_meal >= 5`
- All components get a fallback assignment to "farm" if not caught by earlier rules

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        # Categorize all components
        must_eat = []          # sms >= 5, absolutely forced
        warriors_need_eat = [] # warriors sms 3-4, must eat before cave
        warriors_can_go = []   # warriors sms < 3
        farmers_rest = []      # farmers not forced to eat

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= 5:
                    must_eat.append(c)
                elif c.steps_since_meal >= 3:
                    warriors_need_eat.append(c)
                else:
                    warriors_can_go.append(c)
            else:  # Farmer
                if c.steps_since_meal >= 5:
                    must_eat.append(c)
                else:
                    farmers_rest.append(c)

        # PRIORITY 1: Forced meals (sms >= 5)
        for c in must_eat:
            if wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # PRIORITY 2: Warriors who must eat before going to cave (sms 3-4)
        for c in warriors_need_eat:
            if wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # PRIORITY 3: Proactive eating for warriors with sms=2 going to cave
        # (they'll arrive at sms=3, need one more attack before returning)
        # Don't force eat here; instead check if they should go or eat.

        # PRIORITY 4: Spawning (only if sufficient wheat remains after meals)
        # Need enough wheat reserve for upcoming meals
        remaining_farmers = list(farmers_rest)

        spawn_warrior_pair = []
        spawn_farmer_pair = []

        # Estimate upcoming meal needs (rough reserve)
        meal_reserve = max(len(remaining_farmers) + len(warriors_can_go), 4)

        # Spawn warriors early and mid game for attack power
        if step >= 2 and step <= 14 and len(remaining_farmers) >= 2:
            cost = 12
            if wheat >= cost + meal_reserve:
                spawn_warrior_pair = remaining_farmers[:2]
                remaining_farmers = remaining_farmers[2:]
                wheat -= cost

        # Spawn farmers mid game for wheat production
        if step >= 5 and step <= 18 and len(remaining_farmers) >= 2:
            cost = 10
            if wheat >= cost + meal_reserve:
                spawn_farmer_pair = remaining_farmers[:2]
                remaining_farmers = remaining_farmers[2:]
                wheat -= cost

        for c in spawn_warrior_pair:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer_pair:
            environment.assign_group(c, "spawn farmer")

        # PRIORITY 5: Warriors going to cave with stagger
        to_cave = []
        stay_in_village = []

        if warriors_can_go:
            if step <= 0:
                to_cave = warriors_can_go[:1]
                stay_in_village = warriors_can_go[1:]
            elif step == 1:
                to_cave = warriors_can_go[:1]
                stay_in_village = warriors_can_go[1:]
            else:
                # All available warriors go to cave; natural cycling staggers them
                to_cave = warriors_can_go[:]

        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in stay_in_village:
            # Stay and farm (or eat if sms is getting high)
            if c.steps_since_meal >= 2 and wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # PRIORITY 6: Remaining farmers → farm
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.steps_since_meal >= 3:
                # Must go to village to eat before starving
                environment.assign_group(c, "village")
            else:
                # Attack the dragon
                environment.assign_group(c, "attack")
```