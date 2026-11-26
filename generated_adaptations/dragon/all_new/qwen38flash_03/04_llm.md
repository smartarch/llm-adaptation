

Looking at the test failures, I need to fix several issues:

1. **Dragon not dying** (required): Warriors aren't maintaining sustained attack pressure. I need to send them to cave earlier, keep them attacking longer, and build a larger army.
2. **Not spawning villagers** (optional hint): When population < 5 or no warriors exist, I must spawn from farmers.
3. **Warriors attacking < 2 times in cave**: Need to track cave arrival and enforce minimum attacks.
4. **Never spawning a farmer**: Must spawn at least one.
5. **No farmer/warrior when none exist**: Must spawn warriors when population drops to 0 warriors.

Key strategy changes:
- Build up 7+ warriors aggressively via spawning