# Reasoning and improved adaptation strategy (embedded as comments for a single code block):
# - Goal remains: protect the field with the highest current threat level using drones efficiently.
# - Key improvements over prior versions:
#   1) Include drones that are already en route (state == "moving_to_field") toward the top field as contributing to protection.
#   2) When calculating protection for the top field, count both protecting drones and inbound drones toward that field.
#   3) Do not evict drones that are already protecting the top field if the field is not yet fully protected.
#   4) After allocating to the top field, consider a secondary field if there are enough remaining drones to fully protect it.
#   5) Always assign groups using the exact required group names, and fall back safely to "idle" if a group name is missing.
# - This approach aims to reduce damage faster by:
#   - Minimizing time to full protection for the highest-threat field (using closest drones and inbound ones).
#   - Efficiently utilizing spare drones to provide full protection to a second field when feasible.
#   - Keeping the structure simple and in line with the required group naming.

from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect fields with positive threat levels
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No field needs protection; idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Helper: field center
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # 3) Choose the top field by highest threat_level; tie-break by distance from nearest drone
        best_field = None
        best_threat = -1.0
        best_dist = float("inf")

        for f in fields:
            cx, cy = center_of(f)
            min_dist_to_field = float("inf")
            for d in components:
                dx = d.location.x - cx
                dy = d.location.y - cy
                dist = (dx*dx + dy*dy) ** 0.5
                if dist < min_dist_to_field:
                    min_dist_to_field = dist

            if (f.threat_level > best_threat) or (
                abs(f.threat_level - best_threat) < 1e-9 and min_dist_to_field < best_dist
            ):
                best_field = f
                best_threat = f.threat_level
                best_dist = min_dist_to_field

        if best_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_group = f"protecting {best_field.id}"
        if top_group not in group_ids:
            # Safe fallback if the required group does not exist
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 4) Determine current drones committed to the top field
        top_center = center_of(best_field)
        protecting_indices = []
        incoming_indices = []
        for idx, d in enumerate(components):
            if getattr(d, "target_id", None) == best_field.id:
                if getattr(d, "state", "") == "protecting":
                    protecting_indices.append(idx)
                elif getattr(d, "state", "") == "moving_to_field":
                    incoming_indices.append(idx)

        assigned_indices = set(protecting_indices + incoming_indices)

        # Reflect current intent by assigning these drones to the top field
        for idx in protecting_indices + incoming_indices:
            environment.assign_group(components[idx], top_group)

        # 5) Compute how many drones are needed to reach full protection
        required = int(getattr(best_field, "drones_for_full_protection", 0))
        current_count = len(protecting_indices) + len(incoming_indices)
        needed = max(0, required - current_count)

        # 6) If needed, pick closest available drones to fill the gap
        cx, cy = top_center
        candidates = []
        for idx, d in enumerate(components):
            if idx in assigned_indices:
                continue
            dx = d.location.x - cx
            dy = d.location.y - cy
            dist = (dx*dx + dy*dy) ** 0.5
            candidates.append((dist, idx))
        candidates.sort()

        for i in range(min(needed, len(candidates))):
            idx = candidates[i][1]
            environment.assign_group(components[idx], top_group)
            assigned_indices.add(idx)

        # 7) Optional: second-best field support if possible
        # Find the next highest-threat field (excluding the top field)
        second_field = None
        second_threat = -1.0
        second_best_dist = float("inf")

        for f in fields:
            if f.id == best_field.id:
                continue
            cx2, cy2 = center_of(f)
            min_dist_to_field = float("inf")
            for d in components:
                dx = d.location.x - cx2
                dy = d.location.y - cy2
                dist = (dx*dx + dy*dy) ** 0.5
                if dist < min_dist_to_field:
                    min_dist_to_field = dist
            if f.threat_level > second_threat or (abs(f.threat_level - second_threat) < 1e-9 and min_dist_to_field < second_best_dist):
                second_field = f
                second_threat = f.threat_level
                second_best_dist = min_dist_to_field

        if second_field is not None and second_threat > 0:
            second_group = f"protecting {second_field.id}"
            if second_group in group_ids:
                # Determine how many drones are already protecting/heading to the second field
                second_required = int(getattr(second_field, "drones_for_full_protection", 0))

                # Count drones currently committed to second field
                second_protecting = []
                second_incoming = []
                for idx, d in enumerate(components):
                    if getattr(d, "target_id", None) == second_field.id:
                        if getattr(d, "state", "") == "protecting":
                            second_protecting.append(idx)
                        elif getattr(d, "state", "") == "moving_to_field":
                            second_incoming.append(idx)

                # Only reassign drones we can spare (excluding those already on the top field)
                available_for_second = [
                    (idx) for idx in range(len(components))
                    if idx not in assigned_indices and idx not in second_protecting and idx not in second_incoming
                ]

                # How many more are needed for second field
                second_current = len(second_protecting) + len(second_incoming)
                second_needed = max(0, second_required - second_current)

                # Choose closest drones to second_field to fill second_needed
                if second_needed > 0 and available_for_second:
                    cx2, cy2 = center_of(second_field)
                    cand2 = []
                    for idx in available_for_second:
                        d = components[idx]
                        dx = d.location.x - cx2
                        dy = d.location.y - cy2
                        dist = (dx*dx + dy*dy) ** 0.5
                        cand2.append((dist, idx))
                    cand2.sort()
                    for j in range(min(second_needed, len(cand2))):
                        idx = cand2[j][1]
                        environment.assign_group(components[idx], second_group)
                        assigned_indices.add(idx)

        # 8) Remaining drones go idle
        for idx, d in enumerate(components):
            if idx not in assigned_indices:
                environment.assign_group(d, "idle")