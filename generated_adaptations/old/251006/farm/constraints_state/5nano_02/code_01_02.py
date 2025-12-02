import math
import abc
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat levels
        fields = getattr(environment, "fields", []) or []
        threatening_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute center of a field
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Determine the field to protect (highest threat)
        best_field = None
        if threatening_fields:
            best_field = max(threatening_fields, key=lambda f: getattr(f, "threat_level", 0))

        # If there is no threatened field, keep drones idle or preserve existing actions
        def assign_to_group(drone, group_name):
            if group_name not in group_ids:
                # If the desired group isn't valid, fall back to idle if possible
                if "idle" in group_ids:
                    environment.assign_group(drone, "idle")
                else:
                    # As a last resort, assign to any valid group id or ignore
                    for gid in group_ids:
                        environment.assign_group(drone, gid)
                        break
            else:
                environment.assign_group(drone, group_name)

        if best_field is None:
            # No field to protect: idle all drones, preserving any existing protecting actions if possible
            for drone in components:
                if getattr(drone, "state", None) == "protecting" and getattr(drone, "target_id", None):
                    g = f"protecting {drone.target_id}"
                    assign_to_group(drone, g if g in group_ids else "idle")
                else:
                    assign_to_group(drone, "idle")
            return

        # Compute whether the best field is already fully protected
        best_field_protecting = getattr(best_field, "protecting_drones", 0)
        best_field_arriving = getattr(best_field, "arriving_drones", 0)
        best_field_needed = getattr(best_field, "drones_for_full_protection", 0)
        is_fully_protected = (best_field_protecting + best_field_arriving) >= best_field_needed

        # If not fully protected, allocate the minimum number of drones needed, choosing closest drones
        assignments = {}  # drone -> group_name

        center_x, center_y = center_of(best_field)

        if not is_fully_protected:
            needed = max(0, best_field_needed - (best_field_protecting + best_field_arriving))

            # Candidates: drones not already protecting best_field (and not en route to it)
            candidates = []
            for d in components:
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == best_field.id:
                    # already protecting best_field
                    continue
                if getattr(d, "state", "") == "moving_to_field" and getattr(d, "target_id", None) == best_field.id:
                    # en route to best_field
                    continue
                candidates.append(d)

            # Sort by distance to best_field center
            def dist_to_center(drone):
                loc = getattr(drone, "location", None)
                dx = getattr(loc, "x", 0.0)
                dy = getattr(loc, "y", 0.0)
                return math.hypot(dx - center_x, dy - center_y)

            candidates.sort(key=dist_to_center)

            to_assign = []
            if needed > 0:
                to_assign = candidates[:min(needed, len(candidates))]

            # If not enough candidates, fill with the closest among remaining drones
            if len(to_assign) < needed:
                remaining = [d for d in components if d not in to_assign and d not in to_assign]
                remaining.sort(key=lambda d: dist_to_center(d))
                extra_needed = needed - len(to_assign)
                to_assign.extend(remaining[:extra_needed])

            # Assign chosen drones to the best_field protection group
            grp = f"protecting {best_field.id}"
            for d in to_assign:
                if grp in group_ids:
                    assignments[d] = grp
                else:
                    # Fallback to idle if the group isn't valid
                    assignments[d] = "idle"

        # For drones not yet assigned, decide a reasonable default to preserve or idle
        for d in components:
            if d in assignments:
                continue
            # If the drone is currently protecting some field, keep it assigned to that field's group if possible
            st = getattr(d, "state", "")
            tgt = getattr(d, "target_id", None)
            if st == "protecting" and tgt is not None:
                g = f"protecting {tgt}"
                if g in group_ids:
                    assignments[d] = g
                else:
                    assignments[d] = "idle"
            elif st == "moving_to_field" and tgt is not None:
                g = f"protecting {tgt}"
                if g in group_ids:
                    assignments[d] = g
                else:
                    assignments[d] = "idle"
            else:
                # Idle drones stay idle
                assignments[d] = "idle" if "idle" in group_ids else None

        # Apply assignments
        for drone, group_name in assignments.items():
            if group_name is None:
                continue
            environment.assign_group(drone, group_name)