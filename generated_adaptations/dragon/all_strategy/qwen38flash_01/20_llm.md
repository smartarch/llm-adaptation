

Looking at the failures, I need to fix:
1. **Wheat tracking**: Must subtract wheat locally for each eat/spawn and check before assigning
2. **All components assigned**: Every component must get a group, with proper fallbacks
3. **Dragon gaps > 2**: Must stagger warrior departures (one per step) so their cycles interleave
4. **Warriors