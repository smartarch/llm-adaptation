import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        num_drones = len(components)
        if num_drones == 0:
            return

        # Sort active fields (threat > 0) by threat level descending
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)

        if not active_fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            return

        # Track which drones are already protecting which field (for stability)
        drone_current_field = {}
        for drone in components:
            tid = getattr(drone, 'target_id', None)
            if tid is not None:
                drone_current_field[id(drone)] = tid

        # Assignments: field.id -> list of drone objects
        field_assignments = {f.id: [] for f in active_fields}
        assigned_set = set()

        # Helper to compute distance from drone to field center
        def dist_to_field(drone, field):
            fx = (getattr(field, 'left', 0) + getattr(field, 'right', 0)) / 2.0
            fy = (getattr(field, 'top', 0) + getattr(field, 'bottom', 0)) / 2.0
            dx = getattr(drone, 'x', 0)
            dy = getattr(drone, 'y', 0)
            return math.sqrt((dx - fx) ** 2 + (dy - fy) ** 2)

        # Pass 1: For each field in threat order, fill to drones_for_full_protection
        # Prefer drones already at that field (stability), then closest available
        for field in active_fields:
            need = field.drones_for_full_protection

            # First: keep drones already assigned to this field (stability)
            already_here = [
                d for d in components
                if id(d) not in assigned_set
                and drone_current_field.get(id(d)) == field.id
            ]
            # Sort already-here drones by distance (closest first among already-here)
            already_here.sort(key=lambda d: dist_to_field(d, field))
            for d in already_here:
                if len(field_assignments[field.id]) >= need:
                    break
                field_assignments[field.id].append(d)
                assigned_set.add(id(d))

            # Second: fill remaining slots with closest available drones
            remaining_need = need - len(field_assignments[field.id])
            if remaining_need > 0:
                available = [
                    d for d in components
                    if id(d) not in assigned_set
                ]
                available.sort(key=lambda d: dist_to_field(d, field))
                for d in available[:remaining_need]:
                    field_assignments[field.id].append(d)
                    assigned_set.add(id(d))

        # Pass 2: Handle unassigned drones - ensure at least half are active
        unassigned = [d for d in components if id(d) not in assigned_set]
        min_active = num_drones // 2
        num_active = num_drones - len(unassigned)

        if unassigned and num_active < min_active:
            # Assign remaining drones to fields that still have slots (no overprotection)
            for field in active_fields:
                if num_active >= min_active:
                    break
                capacity = field.drones_for_full_protection - len(field_assignments[field.id])
                if capacity <= 0:
                    continue
                # Sort unassigned by distance to this field
                unassigned.sort(key=lambda d: dist_to_field(d, field))
                to_assign = min(capacity, len(unassigned), min_active - num_active)
                for d in unassigned[:to_assign]:
                    field_assignments[field.id].append(d)
                    assigned_set.add(id(d))
                unassigned = unassigned[to_assign:]
                num_active += to_assign

        # Pass 3: For still-unassigned drones, if they're currently protecting a
        # still-threatened field, keep them there (stability) unless field is full
        for d in unassigned[:]:
            cur = drone_current_field.get(id(d))
            if cur and cur in field_assignments:
                field_obj = next((f for f in active_fields if f.id == cur), None)
                if field_obj and len(field_assignments[cur]) < field_obj.drones_for_full_protection:
                    field_assignments[cur].append(d)
                    assigned_set.add(id(d))
                    unassigned.remove(d)

        # Pass 4: Last resort - if still idle drones and fields need protection,
        # assign to most threatened field not yet fully covered
        while unassigned and active_fields:
            placed = False
            for field in active_fields:
                if len(field_assignments[field.id]) < field.drones_for_full_protection:
                    d = unassigned.pop(0)
                    field_assignments[field.id].append(d)
                    assigned_set.add(id(d))
                    placed = True
                    break
            if not placed:
                break

        # Final: remaining unassigned go to idle
        # Build reverse map: drone id -> field id
        drone_field_map = {}
        for fid, drones in field_assignments.items():
            for d in drones:
                drone_field_map[id(d)] = fid

        for drone in components:
            fid = drone_field_map.get(id(drone))
            if fid is not None:
                environment.assign_group(drone, f"protecting {fid}")
            else:
                environment.assign_group(drone, "idle")