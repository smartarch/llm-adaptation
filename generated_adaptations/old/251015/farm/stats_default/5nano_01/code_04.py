# Reasoning and adaptation strategy (embedded as comments in the code):
#
# Observations from the evaluation:
# - Average damage is relatively high, and the most-threatened field is only about 60% protected.
# - Most drones are being used to protect a single field, while others are under-protected.
# - Drones spend time moving between fields (avg moving_to_field ~ 1.1), which delays protection.
#
# Improved strategy:
# 1) Always prioritize fully protecting the field with the highest threat level using the closest drones.
#    Only reallocate drones if doing so helps reach full protection with the least movement.
# 2) Do not disrupt existing protections on other fields unless necessary to achieve top-field full protection.
# 3) After attempting to fully protect the top field, opportunistically pre-position additional idle (or moving) drones
#    to the next most-threatened fields, but only from drones that are not currently protecting another field (to minimize disruption).
# 4) For all drones, explicitly assign a group each step:
#    - "protecting {field_id}" for drones protecting a field
#    - "idle" for drones not actively protecting a field
# 5) The strategy is greedy and keeps the top field fully protected when possible; it reduces movement by
#    preferring drones that are not currently protecting other fields for any additional protection efforts.
#
# This approach aims to reduce damage by ensuring the most dangerous field is fully protected with nearby drones,
# and by reducing unnecessary drone movements.

import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: distance from a drone to a field center
        def dist_to_field(drone, field_center):
            if getattr(drone, "location", None) is None or drone.location is None:
                return float('inf')
            dx = drone.location.x - field_center[0]
            dy = drone.location.y - field_center[1]
            return math.hypot(dx, dy)

        # Collect fields with positive threat
        threat_fields = []
        for f in getattr(environment, "fields", []):
            th = getattr(f, "threat_level", 0.0) or 0.0
            if th > 0:
                threat_fields.append(f)

        # If nothing is threatened, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threat fields by threat level (desc); tie-breaker by drones_for_full_protection (smaller is more urgent)
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (
                -(f.threat_level if f.threat_level is not None else 0.0),
                getattr(f, "drones_for_full_protection", float('inf'))
            )
        )
        top_field = threat_fields_sorted[0]

        # Center of top field
        top_center = ((top_field.left + top_field.right) / 2.0, (top_field.top + top_field.bottom) / 2.0)

        # Count current protectors on the top field
        current_top_protectors = sum(
            1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id
        )

        target_top = getattr(top_field, "drones_for_full_protection", 0) or 0

        selected_for_top = set()

        # Build candidates for top: not currently protecting top; do not pull drones protecting other fields
        candidates_top = []
        for idx, drone in enumerate(components):
            state = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)

            # Already protecting top: skip
            if state == "protecting" and tid == top_field.id:
                continue
            # If drone is protecting another field, do not pull it (to minimize disruption)
            if state == "protecting" and tid is not None and tid != top_field.id:
                continue

            d = dist_to_field(drone, top_center)
            candidates_top.append((d, idx, drone))

        candidates_top.sort(key=lambda t: t[0])

        needed = max(0, int(target_top) - int(current_top_protectors))
        for i in range(min(needed, len(candidates_top))):
            _, idx, drone = candidates_top[i]
            environment.assign_group(drone, f"protecting {top_field.id}")
            selected_for_top.add(idx)

        # After top is considered, opportunistically pre-position other fields using drones not currently protecting any field
        remaining_fields = threat_fields_sorted[1:]  # second/top other fields
        for field in remaining_fields:
            if field is None:
                continue
            current = sum(
                1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == field.id
            )
            target = getattr(field, "drones_for_full_protection", 0) or 0
            if current >= int(target) or int(target) == 0:
                continue

            field_center = ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

            candidates = []
            for idx, drone in enumerate(components):
                if idx in selected_for_top:
                    continue
                st = getattr(drone, "state", None)
                tid = getattr(drone, "target_id", None)

                # Do not pull drones already protecting another field
                if st == "protecting" and tid is not None:
                    if tid != field.id:
                        continue

                # If drone is idle or moving, consider it; compute distance to this field
                if getattr(drone, "location", None) is None or drone.location is None:
                    dx = dy = 0.0
                else:
                    dx = drone.location.x - field_center[0]
                    dy = drone.location.y - field_center[1]
                d = math.hypot(dx, dy)
                candidates.append((d, idx, drone))

            candidates.sort(key=lambda t: t[0])
            needed2 = int(target) - int(current)
            for i in range(min(needed2, len(candidates))):
                _, idx, drone = candidates[i]
                environment.assign_group(drone, f"protecting {field.id}")

        # Finally, re-assign every drone to a concrete group to satisfy the contract
        for idx, drone in enumerate(components):
            state = getattr(drone, "state", None)
            tid = getattr(drone, "target_id", None)

            if state == "protecting" and tid is not None:
                final_group = f"protecting {tid}"
            else:
                final_group = "idle"

            if final_group not in group_ids:
                final_group = "idle"

            environment.assign_group(drone, final_group)