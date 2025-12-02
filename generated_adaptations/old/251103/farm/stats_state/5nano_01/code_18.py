from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Movement-conscious, global, benefit-based allocation:

        - Build a set of threatening fields (threat_level > 0).
        - For each drone, consider all fields and compute a score:
            score = threat_level * delta_coverage - movement_penalty
            where delta_coverage is the increase in field protection if this drone is added (0 <= delta_coverage <= 1),
            and movement_penalty is proportional to the distance to the field center.
        - Assign drones to the field with the highest positive score, updating provisional counts as we go.
        - Any drone not assigned to a field is set to idle.
        - Only fields with threat_level > 0 receive protection groups.
        """
        # 1) Identify threatening fields
        threatening_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatening_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Prepare per-field data
        field_info = {}
        for f in threatening_fields:
            fid = f.id
            center_x = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            center_y = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0
            field_info[fid] = {
                "field": f,
                "center": (center_x, center_y),
                "drones_for_full_protection": getattr(f, "drones_for_full_protection", 0),
                "protecting": getattr(f, "protecting_drones", 0),
                "arriving": getattr(f, "arriving_drones", 0),
                "threat": getattr(f, "threat_level", 0),
            }

        # 3) Provisional counts start from current values
        provisional_protecting = {fid: info["protecting"] for fid, info in field_info.items()}
        provisional_arriving = {fid: info["arriving"] for fid, info in field_info.items()}

        # 4) Greedily assign drones one by one to the best field
        unassigned = list(components)
        assigned = set()
        while True:
            best = None  # (drone, field_id, score, dist2, delta_cov, field_threat)
            best_score = -1e9

            if not unassigned:
                break

            for d in list(unassigned):
                lx = getattr(d.location, "x", 0.0)
                ly = getattr(d.location, "y", 0.0)

                # Consider every field that still needs protection
                for fid, info in field_info.items():
                    f = info["field"]
                    drones_for_full = info["drones_for_full_protection"]
                    if drones_for_full <= 0:
                        continue

                    protecting = provisional_protecting.get(fid, 0)
                    arriving = provisional_arriving.get(fid, 0)

                    current_cov = min(1.0, (protecting + arriving) / drones_for_full)
                    new_cov = min(1.0, (protecting + arriving + 1) / drones_for_full)
                    delta_cov = new_cov - current_cov
                    threat = info["threat"]
                    gain = delta_cov * threat

                    # Movement penalty; scale distance to field center
                    dx = lx - info["center"][0]
                    dy = ly - info["center"][1]
                    dist2 = dx * dx + dy * dy
                    movement_penalty = dist2 * 1e-4  # tune factor

                    score = gain - movement_penalty

                    if score > best_score:
                        best_score = score
                        best = (d, fid, score, dist2, delta_cov, gain)

            if best is None or best_score <= 0:
                break

            # Assign the best drone to the best field
            drone, fid, score, dist2, delta_cov, gain = best
            environment.assign_group(drone, f"protecting {fid}")
            assigned.add(id(drone))
            unassigned.remove(drone)

            # Update provisional counts for the chosen field
            provisional_protecting[fid] = provisional_protecting.get(fid, 0) + 1

        # 5) Idle all remaining drones
        for d in components:
            if id(d) not in assigned:
                environment.assign_group(d, "idle")