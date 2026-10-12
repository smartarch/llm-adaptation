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

        # Helpers
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist2_to_point(drone, point):
            dx = getattr(drone.location, "x", 0.0) - point[0]
            dy = getattr(drone.location, "y", 0.0) - point[1]
            return dx * dx + dy * dy

        # Threatened fields
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened_fields:
            for d in drones:
                environment.assign_group(d, "idle")
            self._reset_memory()
            return

        # Sort threatened fields by threat_level desc
        threatened_fields_sorted = sorted(threatened_fields,
                                          key=lambda f: getattr(f, "threat_level", 0.0),
                                          reverse=True)

        # Top field
        top_field = threatened_fields_sorted[0]
        top_center = center_of(top_field)
        top_needed = max(0, getattr(top_field, "drones_for_full_protection", len(drones)))
        top_needed = min(top_needed, len(drones))

        dist_to_top = {d: dist2_to_point(d, top_center) for d in drones}

        # Stage 1: protect top field
        top_set = set()

        # Reuse previous top drones if same field
        if self.prev_top_field_id == getattr(top_field, "id", None) and self.prev_top_drones:
            for d in drones:
                if len(top_set) >= top_needed:
                    break
                if id(d) in self.prev_top_drones:
                    top_set.add(d)

        # Fill with closest drones (arrival time ~ dist/2), tie-break to memory
        if len(top_set) < top_needed:
            remaining = [d for d in drones if d not in top_set]
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

        # Stage 2: greedy allocation for other fields (no partial protection)
        # We'll repeatedly pick the best field to fully protect given remaining drones
        while True:
            best_field = None
            best_efficiency = -1.0
            best_needed = 0
            best_set = None

            # Consider each threatened field beyond the top one
            for field in threatened_fields_sorted[1:]:
                needed = max(0, getattr(field, "drones_for_full_protection", 0)
                             - len(self.prev_field_allocations.get(field.id, set())))
                if needed <= 0:
                    continue
                if len(remaining_drones) < needed:
                    continue

                center = center_of(field)
                prev_ids = self.prev_field_allocations.get(field.id, set())

                # Build candidate set for this field
                candidates = []
                if remaining_drones:
                    # Prefer previously allocated drones for this field
                    prev_candidates = [d for d in remaining_drones if id(d) in prev_ids]
                    prev_candidates.sort(key=lambda d: dist2_to_point(d, center))
                    for d in prev_candidates:
                        candidates.append(d)

                if len(candidates) < needed:
                    rest = [d for d in remaining_drones if d not in candidates]
                    rest.sort(key=lambda d: dist2_to_point(d, center))
                    for d in rest:
                        if len(candidates) >= needed:
                            break
                        candidates.append(d)

                if len(candidates) < needed:
                    continue

                total_dist = sum(dist2_to_point(d, center) for d in candidates[:needed])
                efficiency = getattr(field, "threat_level", 0.0) / (total_dist + 1e-9)

                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best_field = field
                    best_needed = needed
                    best_set = set(candidates[:needed])

            if best_field is None:
                break  # no more can be fully protected

            # Allocate best_set to best_field
            for d in best_set:
                allocations[d] = f"protecting {best_field.id}"
            new_field_allocations[best_field.id] = set(id(d) for d in best_set)
            for d in list(best_set):
                if d in remaining_drones:
                    remaining_drones.remove(d)

        # Remaining drones idle
        for d in remaining_drones:
            allocations[d] = "idle"

        # Write groups
        for d in drones:
            environment.assign_group(d, allocations.get(d, "idle"))

        # Update memory
        self.prev_top_field_id = getattr(top_field, "id", None)
        self.prev_top_drones = set(id(d) for d in top_set)
        self.prev_field_allocations = new_field_allocations

    def _reset_memory(self):
        self.prev_top_field_id = None
        self.prev_top_drones = set()
        self.prev_field_allocations = {}

    # Alias for clarity when tests inspect memory (optional)