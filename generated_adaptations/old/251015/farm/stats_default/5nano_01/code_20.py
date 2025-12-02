import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def _field_target_count(self, field, total_drones):
        # Support both absolute and fractional targets
        val = getattr(field, "drones_for_full_protection", 0)
        if val is None:
            val = 0
        try:
            Vf = float(val)
        except (TypeError, ValueError):
            Vf = 0.0
        if Vf <= 1.0:
            # Treat as a fraction of total drones
            return max(0, int(math.ceil(Vf * total_drones)))
        else:
            return max(0, int(Vf))
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helpers
        def dist_to_center(drone, center):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return math.hypot(dx, dy)

        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # 1) Gather threatened fields
        threat_fields = []
        for f in getattr(environment, "fields", []):
            th = getattr(f, "threat_level", 0.0) or 0.0
            if th > 0:
                threat_fields.append(f)

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        total_drones = len(components)

        # 2) Sort threat fields by threat level desc; tie-break by drones_for_full_protection asc
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (
                -(f.threat_level if f.threat_level is not None else 0.0),
                getattr(f, "drones_for_full_protection", float('inf'))
            )
        )
        top_field = threat_fields_sorted[0]
        top_center = field_center(top_field)

        # 3) Compute current protectors per field
        current_by_field = {f.id: 0 for f in threat_fields_sorted}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_by_field:
                    current_by_field[tid] += 1

        # Target counts per field
        target_by_field = {f.id: self._field_target_count(f, total_drones) for f in threat_fields_sorted}
        current_top = current_by_field[top_field.id]
        top_target = target_by_field[top_field.id]

        selected_for_top = set()

        # 4) Aggressively allocate to top_field if needed
        if current_top < top_target and top_target > 0:
            needed = int(top_target) - int(current_top)

            # Build candidate drones: exclude those already protecting top_field
            candidates = []
            for idx, drone in enumerate(components):
                st = getattr(drone, "state", None)
                tid = getattr(drone, "target_id", None)

                if st == "protecting" and tid == top_field.id:
                    continue  # already on top_field

                # Include all drones except those already protecting top_field
                d = dist_to_center(drone, top_center)
                candidates.append((d, idx, drone))

            # Sort by distance (closest first)
            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed, len(candidates))):
                _, idx, drone = candidates[i]
                environment.assign_group(drone, f"protecting {top_field.id}")
                selected_for_top.add(idx)

        # 5) Phase 2: allocate to other threatened fields if there are leftover drones
        assigned_to_field = {}
        remaining_fields = threat_fields_sorted[1:]

        for field in remaining_fields:
            if field is None:
                continue
            field_id = field.id
            target = self._field_target_count(field, total_drones)

            # Recompute current protection for this field after top-field allocations
            current = sum(
                1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field_id
            )
            if current >= target or target == 0:
                continue

            field_center_pos = field_center(field)

            candidates = []
            for idx, drone in enumerate(components):
                if idx in selected_for_top:
                    continue

                st = getattr(drone, "state", None)
                tid = getattr(drone, "target_id", None)

                d = dist_to_center(drone, field_center_pos)
                candidates.append((d, idx, drone))

            candidates.sort(key=lambda t: t[0])
            needed2 = max(0, int(target) - int(current))
            for i in range(min(needed2, len(candidates))):
                _, idx, drone = candidates[i]
                environment.assign_group(drone, f"protecting {field_id}")
                assigned_to_field[idx] = field_id

        # 6) Final concrete assignment for all drones
        for idx, drone in enumerate(components):
            if idx in selected_for_top:
                final_group = f"protecting {top_field.id}"
            elif idx in assigned_to_field:
                final_group = f"protecting {assigned_to_field[idx]}"
            else:
                # If drone was protecting some field (unchanged), keep that protection to minimize disruption
                st = getattr(drone, "state", None)
                tid = getattr(drone, "target_id", None)
                if st == "protecting" and tid is not None:
                    final_group = f"protecting {tid}"
                else:
                    final_group = "idle"

            if final_group not in group_ids:
                final_group = "idle"

            environment.assign_group(drone, final_group)