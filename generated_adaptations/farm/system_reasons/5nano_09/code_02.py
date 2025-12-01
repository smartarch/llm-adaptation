from __future__ import annotations
import math
from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory of last group per drone to help continuity.
        # We use the drone object itself as the key.
        self._last_group_map = {}

    def _center_of_field(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _dist(self, a, b):
        dx = a.x - b[0]
        dy = a.y - b[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components: List, environment, group_ids, step: int):
        drones = list(components)

        # Gather fields with threat > 0
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, idle all drones
        if not threatened_fields:
            for d in drones:
                environment.assign_group(d, "idle")
                self._last_group_map[d] = "idle"
            return

        # Sort threatened fields by threat level (desc), tie-breaker by larger drones_for_full_protection
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helper to select drones for a given field
        def select_drones_for_field(field, needed, allocated_set):
            cx, cy = self._center_of_field(field)
            candidates = []
            target_group = f"protecting {field.id}"
            for d in drones:
                if d in allocated_set:
                    continue
                # distance to field center
                dist = math.hypot(d.location.x - cx, d.location.y - cy)
                last_group = self._last_group_map.get(d, None)
                # Prefer drones already protecting this field
                priority = 0 if last_group == target_group else 1
                candidates.append((priority, dist, d))
            # Sort by priority then distance
            candidates.sort(key=lambda t: (t[0], t[1]))
            chosen = [t[2] for t in candidates[:needed]]
            return chosen

        allocated = set()
        # Step 1: Primary field (most threatened) - fully protect
        top_field = threatened_fields[0]
        top_needed = int(getattr(top_field, "drones_for_full_protection", 0))
        top_needed = max(0, min(top_needed, len(drones)))
        top_drones = select_drones_for_field(top_field, top_needed, allocated)
        for d in top_drones:
            group_name = f"protecting {top_field.id}"
            environment.assign_group(d, group_name)
            self._last_group_map[d] = group_name
            allocated.add(d)

        # If top field already had enough drones previously, we might still have fewer now.
        # Our selection ensures continuity bias but we respect the required number.

        # Step 2: Try to fully protect additional fields with remaining drones
        for field in threatened_fields[1:]:
            if len(allocated) >= len(drones):
                break
            needed = int(getattr(field, "drones_for_full_protection", 0))
            remaining = len(drones) - len(allocated)
            if needed <= 0:
                continue
            if remaining < needed:
                # Not enough drones left to fully protect this field, skip to avoid partial protection
                continue
            drones_for_this_field = select_drones_for_field(field, needed, allocated)
            if len(drones_for_this_field) < needed:
                # Not enough drones available (shouldn't normally happen due to remaining check)
                continue
            for d in drones_for_this_field:
                group_name = f"protecting {field.id}"
                environment.assign_group(d, group_name)
                self._last_group_map[d] = group_name
                allocated.add(d)

        # Step 3: Assign all unallocated drones to idle (to avoid leaving drones unassigned)
        for d in drones:
            if d not in allocated:
                environment.assign_group(d, "idle")
                self._last_group_map[d] = "idle"