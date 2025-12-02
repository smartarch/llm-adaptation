# Reasoning and adaptation strategy (embedded as comments in the code):
#
# Objective:
# - Further reduce damage by ensuring the most threatening field is protected as fully as possible,
#   while minimizing unnecessary drone movement and disruption to other fields.
#
# Key ideas guiding this version:
# 1) Always identify the top-threat field (highest threat_level; tie-break by smaller drones_for_full_protection).
# 2) If the top field is not fully protected, reallocate drones to top_field to reach drones_for_full_protection.
#    Preference is given to drones that are already protecting other fields only if those fields are currently
#    over-protected (i.e., more protectors than drones_for_full_protection), so we don't aggressively cripple others.
# 3) When selecting drones for the top field, prefer the closest available drones to minimize movement.
# 4) After securing the top field (as much as possible), keep existing protections for other fields intact to minimize disruption.
# 5) If no threat exists, idle all drones.
#
# This approach aims to increase the protection coverage of the most-threatened field (towards 1.0)
# while keeping movement and disruption in check.

import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: distance from a drone to a field center
        def dist_to_center(drone, center):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float('inf')
            dx = loc.x - center[0]
            dy = loc.y - center[1]
            return math.hypot(dx, dy)

        # Helper: field center
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Gather threatened fields (threat_level > 0)
        threat_fields = []
        for f in getattr(environment, "fields", []):
            th = getattr(f, "threat_level", 0.0) or 0.0
            if th > 0:
                threat_fields.append(f)

        # If no threats, idle everyone
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threats by threat level desc; tie-break by drones_for_full_protection asc
        threat_fields_sorted = sorted(
            threat_fields,
            key=lambda f: (
                -(f.threat_level if f.threat_level is not None else 0.0),
                getattr(f, "drones_for_full_protection", float('inf'))
            )
        )
        top_field = threat_fields_sorted[0]

        top_center = field_center(top_field)

        # Current protection counts per field
        current_by_field = {f.id: 0 for f in threat_fields_sorted}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_by_field:
                    current_by_field[tid] += 1

        target_by_field = {f.id: int(getattr(f, "drones_for_full_protection", 0) or 0) for f in threat_fields_sorted}
        current_top = current_by_field[top_field.id]
        target_top = target_by_field.get(top_field.id, 0)

        selected_for_top = set()

        # Reallocate to top_field if needed
        if current_top < target_top and target_top > 0:
            needed = int(target_top) - int(current_top)

            # Build candidate drones: exclude those already protecting top_field
            candidates = []
            for idx, drone in enumerate(components):
                st = getattr(drone, "state", None)
                tid = getattr(drone, "target_id", None)

                if st == "protecting" and tid == top_field.id:
                    continue  # already on top_field

                # We prefer pulling from over-provisioned fields (to minimize disruption)
                if st == "protecting" and tid is not None:
                    if current_by_field.get(tid, 0) <= target_by_field.get(tid, 0):
                        continue  # not over-provisioned; skip to avoid disrupting
                d = dist_to_center(drone, top_center)
                candidates.append((d, idx, drone))

            candidates.sort(key=lambda t: t[0])

            for i in range(min(needed, len(candidates))):
                _, idx, drone = candidates[i]
                environment.assign_group(drone, f"protecting {top_field.id}")
                selected_for_top.add(idx)

        # Final assignment: ensure each drone is in a concrete group
        for idx, drone in enumerate(components):
            if idx in selected_for_top:
                final_group = f"protecting {top_field.id}"
            else:
                # If not selected for top, preserve existing protection if any to minimize disruption
                st = getattr(drone, "state", None)
                tid = getattr(drone, "target_id", None)
                if st == "protecting" and tid is not None:
                    final_group = f"protecting {tid}"
                else:
                    final_group = "idle"

            if final_group not in group_ids:
                final_group = "idle"

            environment.assign_group(drone, final_group)