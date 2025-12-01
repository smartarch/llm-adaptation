Reasoning and updated adaptation strategy

Summary of new ideas
- Arrival-time awareness: drones aren’t equally effective in protecting a field at the moment. Drones that are already moving toward a field or are near it should be prioritized based on estimated arrival times to that field. This reduces protection latency for the top threat.
- Stronger stability with memory: continue to remember which field a drone protected in the last step, but bias candidate selection toward that memory only when it doesn’t delay reaching full protection of the top field.
- Two-phase allocation with a hard top-field priority:
  - Phase 1: fully protect the most threatened field using the closest drones, with a bias toward drones that previously protected that field.
  - Phase 2: use any remaining drones to protect other threatened fields, but only if doing so helps maintain a healthy protection level (e.g., reach at least half of drones protecting when possible). Use memory bias to prefer drones that previously protected those fields.
- Avoid over-protection and manage churn: never assign more drones than drones_for_full_protection to a field. Preserve drones on their current target when possible, but reallocate if it meaningfully improves protection for top fields with minimal churn.
- Stability first, speed second: prioritize reducing protection latency for the top field, but avoid unnecessary reassignments that would degrade already-protected fields.

What changes in code
- Introduce per-drone memory self._last_target_by_drone (field id or None) to bias reassignment.
- Treat drones that are moving_to_field as contributing toward protection (consistent with early decisions).
- When selecting candidates for top field, sort by (memory_bias, arrival_time_to_field, distance_to_field).
- After top field is full, optionally bolster other threatened fields using a similar memory-aware, arrival-time biased selection, but only to reach at least half protection when feasible.
- Update last-target memory after finalizing assignments.

Python code

```py
from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persist across steps: map drone_id -> last_protected_field_id (string) or None
        self._last_target_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields (threat_level > 0)
        fields = list(getattr(environment, "fields", []))
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, idle all drones and reset memory
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            for d in components:
                self._last_target_by_drone[id(d)] = None
            return

        # 2) Compute field centers for distance calculations
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top  + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # 3) Helper: determine current group for a drone (considers moving_to_field as protection)
        def current_group(d):
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            if st in ("protecting", "moving_to_field") and tid is not None:
                return f"protecting {tid}"
            return "idle"

        # 4) Start with the current assignment as the baseline
        final_group = {d: current_group(d) for d in components}

        # 5) Sort threatened fields by threat descending
        threatened_sorted = sorted(
            threatened_fields,
            key=lambda ff: getattr(ff, "threat_level", 0),
            reverse=True
        )

        # 6) Phase 1: Fully protect the top-threat field
        top_field = threatened_sorted[0]
        top_grp = f"protecting {top_field.id}"
        current_top_protectors = sum(1 for d in components if final_group.get(d) == top_grp)
        needed_top = int(getattr(top_field, "drones_for_full_protection", 0)) - current_top_protectors
        if needed_top > 0:
            cx, cy = field_centers[top_field.id]
            candidates = []
            for d in components:
                if final_group.get(d) == top_grp:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist = sqrt(dx*dx + dy*dy)
                # arrival time to top field
                if getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == top_field.id:
                    arrival = 0.0
                else:
                    arrival = dist / 2.0  # speed = 2
                # memory bias: prefer drones that previously protected this field
                last_match = (self._last_target_by_drone.get(id(d)) == top_field.id)
                candidates.append((0 if last_match else 1, arrival, dist, d))
            candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            for _, _, _, d in candidates[:max(0, needed_top)]:
                final_group[d] = top_grp

        # 7) Phase 2: Optionally bolster other threatened fields if beneficial
        # We add to other fields only if it helps reach at least half protection and top is already protected
        total_drones = len(components)
        half = (total_drones + 1) // 2
        current_protectors = sum(1 for d in components if final_group.get(d, "idle").startswith("protecting "))
        if current_protectors < half:
            for f in threatened_sorted[1:]:
                grp = f"protecting {f.id}"
                current_count = sum(1 for d in components if final_group.get(d) == grp)
                if current_count >= int(getattr(f, "drones_for_full_protection", 0)):
                    continue
                cx, cy = field_centers[f.id]
                candidates = []
                for d in components:
                    if final_group.get(d) == grp:
                        continue
                    loc = getattr(d, "location", None)
                    if loc is None:
                        dist = float("inf")
                    else:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = sqrt(dx*dx + dy*dy)
                    if getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == f.id:
                        arrival = 0.0
                    else:
                        arrival = dist / 2.0
                    last_match = (self._last_target_by_drone.get(id(d)) == f.id)
                    candidates.append((0 if last_match else 1, arrival, dist, d))
                candidates.sort(key=lambda t: (t[0], t[1], t[2]))
                needed = int(getattr(f, "drones_for_full_protection", 0)) - current_count
                if needed <= 0:
                    continue
                for _, _, _, d in candidates[:needed]:
                    final_group[d] = grp
                    current_protectors += 1
                    if current_protectors >= half:
                        break

        # 8) Phase 3: Update memory of last target per drone
        for d in components:
            g = final_group.get(d, "idle")
            if isinstance(g, str) and g.startswith("protecting "):
                field_id = g.split(" ", 1)[1]
                self._last_target_by_drone[id(d)] = field_id
            else:
                self._last_target_by_drone[id(d)] = None

        # 9) Final assignment to environment
        for d in components:
            grp = final_group.get(d, "idle")
            environment.assign_group(d, grp)
```