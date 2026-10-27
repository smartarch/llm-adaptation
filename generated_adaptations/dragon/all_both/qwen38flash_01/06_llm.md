

Looking at the test failures, the main issues are:

1. **Dragon attack gaps >2 steps**: Warriors were being sent to cave with `sms=1` or `sms=2`, arriving with high `sms`, getting only 1 attack (or 0), causing larger gaps in coverage.
2. **Initial stagger not working**: Both warriors leaving at step 0/1 caused them to be in sync, creating 2-step gaps when both return simultaneously.
3. **Not enough warriors spawned**: Too restrictive wheat checks prevented spawning.

**Key Fix**: Warriors should ONLY go to cave when `sms == 0` (arrives at cave with `sms=1`, attacks twice for 6-step cycle). This ensures proper attack windows and natural staggering. Initial deployment sends 1 warrior at step 0, remaining eat first then go ~2 steps later, creating offset that prevents simultaneous returns.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        # Categorize all components
        forced_eat = []       # sms >= 5: must eat now
       