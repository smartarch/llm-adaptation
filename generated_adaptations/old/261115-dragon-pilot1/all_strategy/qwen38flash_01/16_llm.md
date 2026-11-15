

Looking at the failures, I identified these issues:
1. **Invalid assignments**: Trying to "eat" or "spawn" without checking wheat availability
2. **Unassigned components**: When wheat runs out, some components weren't assigned fallback groups
3. **Dragon gaps**: Warriors weren't properly cycling (ssm=4 in cave means next attack → ssm=5 → violation). Must leave at ssm≥4.
4. **Staggering**: Sending one warrior per step from village creates offset-1 cycles (max 2-step gaps, allowed)

Key fixes: check wheat before each eat/spawn assignment, use ssm≥4 as eat threshold in village (ssm=4 going to cave → arrive ssm=5 → can't eat in cave → violation), leave cave at ssm≥4.

```py
from