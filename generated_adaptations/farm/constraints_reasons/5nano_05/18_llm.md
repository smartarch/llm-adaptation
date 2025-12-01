Reasoning and strategy description

Issue fix:
- The test failure shows overprotection: some fields received more drones than their drones_for_full_protection value in a single step. To guarantee correctness, we must ensure no field receives more drones than drones_for_full_protection in the current allocation step.
- The safest approach is to allocate in two clear passes:
  1) Protect the top field with exactly drones_for_full_protection drones (or as many as are available if fewer).
  2) For other threatened fields, attempt to fully protect each one exactly to its drones_for_full_protection, in threat-descending order, using the remaining drones. Do not attempt to reallocate or “greedily” re-check fields after each allocation. If there aren’t enough drones to fully protect a field, skip it (no partial protection), which matches the strategy preference.

Key improvements:
- Two-stage, single-pass allocation for non-top fields. This avoids the previous iterative re-evaluation that could cause overprotection in edge cases.
- Explicit cap: every field gets allocated at most drones_for_full_protection drones in this step.
- Time-to-arrival bias for the top field uses distance/2 as the primary criterion and memory-based tie-breaks to keep some drones on the same field across steps.
- Memory usage preserved to promote stability: remember top-field drones and per-field allocations, but memory is used only to bias the one-step decision, not to circumvent the strict cap rule.

Strategy outline (updated):
1) Identify threatened fields (threat_level > 0). If none, idle all drones and reset memory.
2) Sort threatened fields by threat_level descending and pick the top field.
3) Allocate drones to the top field:
   - Reuse drones from the previous step if they protected the top field.
   - Fill remaining slots with the closest drones to the top field center, biased by previously protecting the top field.
4) Allocate other threatened fields in threat-descending order, but each field can receive at most drones_for_full_protection drones:
   - For each field, compute needed = drones_for_full_protection - number of drones allocated to that field in the previous step.
   - If needed > 0 and there are enough remaining drones, select exactly needed drones. Prefer drones that previously protected this field; otherwise pick the closest remaining drones.
   - Do not allocate to a field if you cannot reach its full protection quota in this step.
5) Drones not allocated become idle.
6) Update memory for the next step (top-field id, top-field drones, per-field allocations).

Code (Python):

```py
from __future__ import annotations
import math
from generated_adaptations.base_classes.farm import FarmAdaptation as BaseFarmAdaptation

class SmartFarmAdaptation(BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory to help stability across steps
        # - prev_top_field_id: id of the field that was top field in the previous step
        # - prev_top_drones: set of drone object ids that protected the top field in the previous step
        # - prev_field_allocations: mapping field_id -> set of drone ids that protected that field in the previous step
        self.prev_top_field_id = None
        self.prev_top_drones = set()
        self.prev_field_allocations = {}  # field_id -> set(drone_id)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        fields = list(environment.fields)

        # Helper to compute field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Helper to compute squared distance between a drone and a point
        def dist2_to_point(drone, point):
            dx = getattr(drone.location, "x", 0.0) - point[0]
            dy = getattr(drone.location, "y", 0.0) - point[1]
            return dx * dx + dy * dy

        # Filter threatened fields
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened_fields:
            # No threat: put all drones idle
            for d in drones:
                environment.assign_group(d, "idle")
            # Clear memory
            self.prev_top_field_id = None
            self.prev_top_drones = set()
            self.prev_field_allocations = {}
            return

        # Sort threatened fields by threat level (desc)
        threatened_fields_sorted = sorted(threatened_fields,
                                          key=lambda f: getattr(f, "threat_level", 0.0),
                                          reverse=True)

        # Top (most threatened) field
        top_field = threatened_fields_sorted[0]
        top_center = center_of(top_field)
        top_needed = max(0, getattr(top_field, "drones_for_full_protection", len(drones)))
        top_needed = min(top_needed, len(drones))

        # Prepare distance map for all drones to top field
        dist_to_top = {d: dist2_to_point(d, top_center) for d in drones}

        # Build initial top_set using memory and time-to-arrival bias
        top_set = set()

        # 1) Try to keep drones that protected the top field in the previous step
        if self.prev_top_field_id == getattr(top_field, "id", None) and self.prev_top_drones:
            for d in drones:
                if len(top_set) >= top_needed:
                    break
                if id(d) in self.prev_top_drones:
                    top_set.add(d)

        # 2) Fill remaining slots with closest available drones
        if len(top_set) < top_needed:
            remaining = [d for d in drones if d not in top_set]
            # Time-to-arrival bias: closer drones first; tie-breaker favors previously-protecting drones
            remaining.sort(key=lambda d: (
                dist_to_top.get(d, dist2_to_point(d, top_center)) / 2.0,
                0 if id(d) in self.prev_top_drones else 1
            ))
            for d in remaining:
                if len(top_set) >= top_needed:
                    break
                top_set.add(d)

        allocations = {}
        for d in top_set:
            allocations[d] = f"protecting {top_field.id}"

        remaining_drones = [d for d in drones if d not in top_set]

        new_field_allocations = {}
        new_field_allocations[top_field.id] = set(id(d) for d in top_set)

        # Allocate to other threatened fields in descending threat order
        for field in threatened_fields_sorted[1:]:
            # Determine how many drones we want to allocate to fully protect this field
            needed = max(0, getattr(field, "drones_for_full_protection", 0)
                         - len(self.prev_field_allocations.get(field.id, set())))
            if needed <= 0:
                continue

            center = center_of(field)
            prev_ids = self.prev_field_allocations.get(field.id, set())

            # Build the candidate set for this field
            keep = set()
            if remaining_drones:
                # First, try drones that were previously allocated to this field
                prev_candidates = [d for d in remaining_drones if id(d) in prev_ids]
                prev_candidates.sort(key=lambda d: dist2_to_point(d, center))
                for d in prev_candidates:
                    if len(keep) >= needed:
                        break
                    keep.add(d)

            # If not enough, fill with closest remaining drones
            if len(keep) < needed and remaining_drones:
                rest_candidates = [d for d in remaining_drones if d not in keep]
                rest_candidates.sort(key=lambda d: dist2_to_point(d, center))
                for d in rest_candidates:
                    if len(keep) >= needed:
                        break
                    keep.add(d)

            # If we have enough, assign exactly 'needed' drones to this field
            if len(keep) == needed:
                for d in keep:
                    allocations[d] = f"protecting {field.id}"
                new_field_allocations[field.id] = set(id(d) for d in keep)
                # Remove allocated drones from pool
                for d in list(keep):
                    if d in remaining_drones:
                        remaining_drones.remove(d)
            else:
                # Not enough to fully protect this field; skip (no partial protection)
                pass

        # Assign any drones not allocated to idle
        for d in remaining_drones:
            allocations[d] = "idle"

        # Write groups for all drones
        for d in drones:
            group = allocations.get(d, "idle")
            environment.assign_group(d, group)

        # Update memory for next step
        self.prev_top_field_id = getattr(top_field, "id", None)
        self.prev_top_drones = set(id(d) for d in top_set)
        self.prev_field_allocations = new_field_allocations
```