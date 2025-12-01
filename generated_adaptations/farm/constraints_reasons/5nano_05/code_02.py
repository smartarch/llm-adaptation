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
        top_needed = getattr(top_field, "drones_for_full_protection", len(drones))

        # Prepare distance map for all drones to top field
        dist_to_top = {d: dist2_to_point(d, top_center) for d in drones}

        # Build initial top_set using memory and closeness
        top_set = set()

        # 1) Try to keep drones that protected the top field in the previous step
        if self.prev_top_field_id == getattr(top_field, "id", None) and self.prev_top_drones:
            # Add as many as possible up to top_needed
            prev_top_objs = [d for d in drones if id(d) in self.prev_top_drones]
            for d in prev_top_objs:
                if len(top_set) >= top_needed:
                    break
                top_set.add(d)

        # 2) Fill remaining slots with closest available drones
        if len(top_set) < top_needed:
            remaining = [d for d in drones if d not in top_set]
            remaining.sort(key=lambda d: dist_to_top.get(d, dist2_to_point(d, top_center)))
            for d in remaining:
                if len(top_set) >= top_needed:
                    break
                top_set.add(d)

        # Assign top field protection
        allocations = {}  # drone -> group_id to assign
        for d in top_set:
            allocations[d] = f"protecting {top_field.id}"

        # Remaining drones after allocating to top field
        remaining_drones = [d for d in drones if d not in top_set]

        # Prepare memory for field allocations (used for stability)
        new_field_allocations = {}

        # Pre-populate with top field allocation
        new_field_allocations[top_field.id] = set(id(d) for d in top_set)

        # Allocate to other threatened fields in descending threat order
        # Exclude the top field from this loop
        for field in threatened_fields_sorted[1:]:
            # Determine how many drones we want to allocate to fully protect this field
            needed = getattr(field, "drones_for_full_protection", 0)
            # Current protection count from previous step (best effort)
            current = len(self.prev_field_allocations.get(field.id, set()))
            remaining_need = max(0, needed - current)
            if remaining_need <= 0:
                # Nothing to allocate to this field this step
                continue

            # Try to preserve drones that previously protected this field
            center = center_of(field)
            keep = set()
            if remaining_drones:
                prev_for_field = self.prev_field_allocations.get(field.id, set())
                # Attempt to reuse previous drones that are still available
                for d in list(prev_for_field):
                    if len(keep) >= remaining_need:
                        break
                    if id(d) in [id(x) for x in remaining_drones]:
                        keep.add(d)
                        if d in remaining_drones:
                            remaining_drones.remove(d)

            # If still need more, pick closest among remaining
            if len(keep) < remaining_need and remaining_drones:
                # Sort remaining by distance to this field
                rem_sorted = sorted(remaining_drones, key=lambda d: dist2_to_point(d, center))
                for d in rem_sorted:
                    if d in keep:
                        continue
                    keep.add(d)
                    remaining_drones.remove(d)
                    if len(keep) >= remaining_need:
                        break

            # Assign these drones to this field if any
            if keep:
                for d in keep:
                    allocations[d] = f"protecting {field.id}"
                new_field_allocations[field.id] = set(id(d) for d in keep)

        # Assign any drones not allocated to idle
        for d in remaining_drones:
            allocations[d] = "idle"

        # Write groups for all drones (ensure all drones are assigned)
        for d in drones:
            group = allocations.get(d, "idle")
            # Guard: only assign groups that exist in group_ids (should be true)
            environment.assign_group(d, group)

        # Update memory for next step
        self.prev_top_field_id = getattr(top_field, "id", None)
        self.prev_top_drones = set(id(d) for d in top_set)
        self.prev_field_allocations = new_field_allocations