Reasoning and adaptation strategy

Goal improvement:
- The previous approaches often focused on either a single top field or a fixed multi-field plan. To push damage lower, we should explicitly maximize the number of fully protected fields first (subject to per-field caps and current protectors), using a budget-aware, proximity-guided selection. After maximizing full protections, we allocate any remaining drones to partially protect the remaining threatened fields, prioritizing higher-threat fields and minimizing travel time.

Key elements of the new strategy:
- Phase A: Preserve existing protectors by explicitly assigning them to their current protect group.
- Phase B (maximize fully protected fields with a cheap-first, proximity-aware heuristic):
  - For each threatened field, compute how many extra drones are needed to reach drones_for_full_protection.
  - Consider fields in ascending order of needed drones (cheapest to fulfill first), to maximize the number of fully protected fields that can be achieved with the available drones.
  - Among fields with the same needed count, break ties by higher threat_level, and then by lower distanceCost (sum of distances of the selected drones to the field center).
  - Allocate the closest available drones to each chosen field up to its needed count.
- Phase C: Partial protection pass:
  - With the remaining drones, distribute them to still-threatened fields in descending threat order, always choosing the closest available drones to each field’s center, up to the per-field cap.
- All drones are assigned to a group: either a “protecting {field_id}” group or idle.

This approach aims to increase the number of fully protected fields first (especially those with high threat), then improve protection on other threatened fields with minimal travel time, using explicit group assignments.

Python code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        n = len(components)

        # 2) Precompute field centers
        centers = {}
        for f in threat_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # 3) Sort fields by threat level (high to low)
        threat_fields_sorted = sorted(
            threat_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True
        )

        plan = {}        # drone_index -> group_name
        allocated = set()  # indices already allocated to a plan

        # Phase A: preserve existing protectors explicitly
        for f in threat_fields_sorted:
            group = f"protecting {f.id}"
            for i, c in enumerate(components):
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                    plan[i] = group
                    allocated.add(i)

        # Helper to compute current count for a field in plan
        def current_for(field):
            group = f"protecting {field.id}"
            return sum(1 for i in range(n) if plan.get(i) == group)

        # Phase B: maximize fully protected fields with a cheap-first, proximity-aware heuristic
        # Build candidate fields with their "needed" drones to reach full protection
        candidates_for_full = []
        for f in threat_fields_sorted:
            cap = int(getattr(f, "drones_for_full_protection", 0))
            current = current_for(f)
            needed = max(0, cap - current)
            if needed > 0:
                cx, cy = centers[f.id]
                # compute distance cost using current available drones (not allocated yet)
                avail = [i for i in range(n) if i not in allocated]
                if not avail:
                    continue
                dists = []
                for idx in avail:
                    loc = getattr(components[idx], "location", None)
                    if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                        dist = float("inf")
                    else:
                        dx = loc.x - cx
                        dy = loc.y - cy
                        dist = (dx*dx + dy*dy) ** 0.5
                    dists.append((dist, idx))
                dists.sort(key=lambda t: t[0])
                dist_cost = sum(d for d, _ in dists[:needed]) if len(dists) >= needed else float("inf")
                candidates_for_full.append((needed, -getattr(f, "threat_level", 0), dist_cost, f))
        # Sort by: smaller needed first, higher threat, smaller distance cost
        candidates_for_full.sort(key=lambda t: (t[0], t[1], t[2]))

        for needed, neg_threat, dist_cost, f in candidates_for_full:
            cap = int(getattr(f, "drones_for_full_protection", 0))
            group = f"protecting {f.id}"
            current = current_for(f)
            to_take = max(0, cap - current)
            if to_take <= 0:
                continue

            avail = [i for i in range(n) if i not in allocated]
            if not avail:
                break

            cx, cy = centers[f.id]
            dists = []
            for idx in avail:
                loc = getattr(components[idx], "location", None)
                if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                    dist = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist = (dx*dx + dy*dy) ** 0.5
                dists.append((dist, idx))
            dists.sort(key=lambda t: t[0])

            for _, idx in dists[:to_take]:
                plan[idx] = group
                allocated.add(idx)

        # Phase C: Partial distribution (allocate remaining drones to still-threatened fields)
        remaining = [i for i in range(n) if i not in allocated]

        for f in threat_fields_sorted:
            if not remaining:
                break
            group = f"protecting {f.id}"
            cx, cy = centers[f.id]
            cap = int(getattr(f, "drones_for_full_protection", 0))

            current = sum(1 for i in range(n) if plan.get(i) == group)
            needed_partial = max(0, cap - current)
            if needed_partial <= 0:
                continue

            for _ in range(needed_partial):
                if not remaining:
                    break
                best_idx = None
                best_dist = float("inf")
                for idx in list(remaining):
                    loc = getattr(components[idx], "location", None)
                    if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                        continue
                    d = (loc.x - cx)**2 + (loc.y - cy)**2
                    if d < best_dist:
                        best_dist = d
                        best_idx = idx
                if best_idx is None:
                    break
                plan[best_idx] = group
                allocated.add(best_idx)
                remaining.remove(best_idx)

        # Final assignment: every drone must be in a group
        for i in range(n):
            environment.assign_group(components[i], plan.get(i, "idle"))
```