Reasoning and adaptation strategy

Goal:
- Improve drone allocation to reduce bird damage by distributing protection across multiple threatened fields rather than focusing only on the single highest-threat field.

Key ideas:
- Use a multi-field, proportional allocation strategy. Allocate drones to fields in proportion to their threat levels, but cap allocations by each field’s drones_for_full_protection.
- After the proportional allocation, if drones remain, distribute them to still-threatened fields in descending threat order to push more fields toward full protection when possible.
- Explicitly assign drones to the target groups ("protecting {field_id}") and ensure all drones are assigned (idle if not allocated to any field).
- Preserve proximity-based selection: when adding drones to a field, choose the closest available drones to that field’s center to minimize travel time.
- Re-assign existing protectors as needed but try to minimize unnecessary movement; any drone must be assigned to exactly one group each step.

This approach aims to increase the number of fully protected fields while still providing meaningful (partial) protection to other fields, reducing the total damage compared to single-field strategies.

Python code

```py
from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect all fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        total_drones = len(components)

        # 2) Precompute field centers
        centers = {}
        for f in threat_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # 3) Sort fields by threat level (high to low)
        threat_fields_sorted = sorted(
            threat_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True
        )

        # 4) Proportional allocation with cap by drones_for_full_protection
        total_threat = sum(getattr(f, "threat_level", 0) for f in threat_fields_sorted) or 1.0
        per_field_target = {}
        allocated = 0

        for f in threat_fields_sorted:
            cap = int(getattr(f, "drones_for_full_protection", 0))
            # proportional target
            proportional = int((getattr(f, "threat_level", 0) / total_threat) * total_drones)
            target = min(proportional, cap)
            if target < 0:
                target = 0
            per_field_target[f.id] = target
            allocated += target

        # distribute any remaining drones up to caps
        remaining = max(0, total_drones - allocated)
        if remaining > 0:
            for f in threat_fields_sorted:
                cap = int(getattr(f, "drones_for_full_protection", 0))
                current = per_field_target.get(f.id, 0)
                can_add = max(0, cap - current)
                add = min(remaining, can_add)
                per_field_target[f.id] = current + add
                remaining -= add
                if remaining == 0:
                    break

        # 5) Build final plan: assign drones to fields to meet per_field_target
        plan = {}            # drone_index -> group_name
        allocated_indices = set()

        # Phase: preserve existing protectors as far as possible
        for f in threat_fields_sorted:
            group = f"protecting {f.id}"
            cx, cy = centers[f.id]

            # Current protectors for this field
            current_protect_indices = [
                i for i, c in enumerate(components)
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
            ]
            for idx in current_protect_indices:
                plan[idx] = group
                allocated_indices.add(idx)

        # Phase: ensure per-field targets are met using closest drones
        for f in threat_fields_sorted:
            group = f"protecting {f.id}"
            target = int(per_field_target.get(f.id, 0))
            # count how many already planned for this field
            current_planned = sum(1 for idx, g in plan.items() if g == group)
            needed = max(0, target - current_planned)
            if needed <= 0:
                continue

            # candidates: drones not yet allocated to any group
            candidates = [i for i in range(len(components)) if i not in allocated_indices]
            if not candidates:
                break

            cx, cy = centers[f.id]
            dist_list = []
            for idx in candidates:
                loc = getattr(components[idx], "location", None)
                if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                    d2 = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    d2 = dx*dx + dy*dy
                dist_list.append((d2, idx))
            dist_list.sort(key=lambda t: t[0])

            for _, idx in dist_list[:needed]:
                plan[idx] = group
                allocated_indices.add(idx)

        # 6) Assign remaining drones to idle
        for i in range(len(components)):
            if i in plan:
                environment.assign_group(components[i], plan[i])
            else:
                environment.assign_group(components[i], "idle")
```