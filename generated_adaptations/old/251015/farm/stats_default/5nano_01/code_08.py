# Reasoning and adaptation strategy (embedded as comments in the code):
#
# Objective:
# - Improve protection by aggressively ensuring the top-threat field is fully protected
#   using the closest available drones while minimizing disruption and movement.
#
# Key ideas:
# - Identify the field with the highest threat level (top_field).
# - If top_field is not fully protected (current_protectors < drones_for_full_protection),
#   reallocate the closest drones that are not currently protecting any field to top_field
#   until full protection is achieved.
# - Do not pull drones that are already protecting other fields (to minimize disruption).
# - If a drone is currently protecting the top_field, keep it in that group (unless it was
#   explicitly selected as a closer drone for top_field).
# - After ensuring the top field, do not aggressively reallocate drones to other fields to avoid
#   increasing movement; the priority is to minimize movement and maximize top_field protection.
# - Finally, assign every drone to a concrete group (protecting top_field, protecting other fields, or idle)
#   based on their current or new targets. If a drone is actively protecting another field and we did not
#   reassign it, keep its protection to minimize disruption.
#
# This approach aims to reduce average damage by guaranteeing the most-threatened field is fully protected
# with nearby drones while keeping the rest of the fleet stable and minimizing movement.

import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: distance from a drone to a field center
        def dist_to_field(drone, center):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return math.hypot(dx, dy)

        # Center of a field
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

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

        # Center of the top field
        top_center = field_center(top_field)

        # Count current protectors on the top field
        current_top_protectors = sum(
            1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id
        )

        target_top = int(getattr(top_field, "drones_for_full_protection", 0) or 0)

        selected_for_top = set()

        # If the top field is not yet fully protected, select the closest drones to fill
        if current_top_protectors < target_top and target_top > 0:
            needed = target_top - current_top_protectors

            # Candidates: all drones that are not currently protecting any field
            candidates = []
            for idx, drone in enumerate(components):
                state = getattr(drone, "state", None)
                tid = getattr(drone, "target_id", None)

                # Do not pull drones already protecting the top field
                if state == "protecting" and tid == top_field.id:
                    continue

                # Only pull drones that are not protecting some other field (to minimize disruption)
                if state == "protecting" and tid is not None and tid != top_field.id:
                    continue

                d = dist_to_field(drone, top_center)
                candidates.append((d, idx, drone))

            # Sort by distance (closest first)
            candidates.sort(key=lambda t: t[0])

            # Pick up to 'needed' drones
            for i in range(min(needed, len(candidates))):
                _, idx, drone = candidates[i]
                environment.assign_group(drone, f"protecting {top_field.id}")
                selected_for_top.add(idx)

        # Final assignment: assign drones to concrete groups
        for idx, drone in enumerate(components):
            final_group = None

            # If drone was selected to top field
            if idx in selected_for_top:
                final_group = f"protecting {top_field.id}"
            else:
                # If drone is already protecting the top field, keep it there
                if getattr(drone, "state", None) == "protecting" and getattr(drone, "target_id", None) == top_field.id:
                    final_group = f"protecting {top_field.id}"
                # If drone is protecting some other field, keep that protection to minimize disruption
                elif getattr(drone, "state", None) == "protecting" and getattr(drone, "target_id", None) is not None:
                    final_group = f"protecting {drone.target_id}"
                else:
                    final_group = "idle"

            if final_group not in group_ids:
                final_group = "idle"

            environment.assign_group(drone, final_group)