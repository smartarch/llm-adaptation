from __future__ import annotations
import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation as BaseFarmAdaptation

class SmartFarmAdaptation(BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory to help stability across steps
        # Store as:
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

        # Prepare distance map for all drones to top field
        dist_to_top = {d: dist2_to_point(d, top_center) for d in drones}

        # Build initial top_set using memory and proximity bias
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
            remaining.sort(key=lambda d: (
                dist_to_top.get(d, dist2_to_point(d, top_center)),
                -(1 if (self.prev_top_field_id == getattr(top_field, "id", None) and id(d) in self.prev_top_drones) else 0)
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
            needed = max(0, getattr(field, "drones_for_full_protection", 0) - len(self.prev_field_allocations.get(field.id, set())))
            if needed <= 0:
                continue

            center = center_of(field)
            prev_ids = self.prev_field_allocations.get(field.id, set())
            candidate = []
            for d in remaining_drones:
                score = dist2_to_point(d, center)
                if id(d) in prev_ids:
                    score -= 1  # bias toward reusing previous drones for this field
                candidate.append((score, d))
            candidate.sort(key=lambda x: x[0])
            chosen = [d for _, d in candidate[:needed]]
            if chosen:
                for d in chosen:
                    allocations[d] = f"protecting {field.id}"
                new_field_allocations[field.id] = set(id(d) for d in chosen)
                for d in chosen:
                    if d in remaining_drones:
                        remaining_drones.remove(d)

        # Any remaining drones become idle
        for d in remaining_drones:
            allocations[d] = "idle"

        # Write groups for all drones
        for d in drones:
            environment.assign_group(d, allocations.get(d, "idle"))

        # Update memory for next step
        self.prev_top_field_id = getattr(top_field, "id", None)
        self.prev_top_drones = set(id(d) for d in top_set)
        self.prev_field_allocations = new_field_allocations