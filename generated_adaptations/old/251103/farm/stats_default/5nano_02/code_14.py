import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, idle everyone
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Sort threat fields by threat level (high to low)
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        total_drones = len(components)

        # 3) Build initial assignment map from current targeting (preserve existing commitments)
        assigned = {}
        for c in components:
            tid = getattr(c, "target_id", None)
            if tid is not None:
                assigned[c] = tid  # drone -> field_id

        # 4) Determine target_set: as many top fields as possible to full protection
        target_set = []
        cum = 0
        first = threat_fields[0]
        first_r = int(getattr(first, "drones_for_full_protection", 0))

        if first_r > 0 and first_r <= total_drones:
            target_set.append(first)
            cum += first_r
            for f in threat_fields[1:]:
                r = int(getattr(f, "drones_for_full_protection", 0))
                if r <= 0:
                    continue
                if cum + r <= total_drones:
                    target_set.append(f)
                    cum += r
                else:
                    break
        else:
            # If even the top field cannot be fully protected, concentrate all drones on the top field
            for c in components:
                environment.assign_group(c, f"protecting {first.id}")
            return

        target_ids = [f.id for f in target_set]

        # 5) For each field in target_set, ensure it has enough drones
        for idx, f in enumerate(target_set):
            fid = f.id
            current = sum(1 for c in components if assigned.get(c) == fid)
            needed = int(getattr(f, "drones_for_full_protection", 0)) - current
            if needed <= 0:
                continue

            cx, cy = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

            higher_ids = set([tf.id for tf in target_set[:idx]])  # higher priority fields

            # Candidates: not already protecting this field and not from higher priority fields
            candidates = []
            for d in components:
                if assigned.get(d) == fid:
                    continue
                t = getattr(d, "target_id", None)
                if t in higher_ids:
                    continue
                # Prefer drones not currently assigned to a target field
                if t not in target_ids:
                    candidates.append(d)
                else:
                    # If drone is on a lower-priority target field, allow only if it won't disturb higher-priority fields
                    candidates.append(d)

            def dist2(d):
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                return dx*dx + dy*dy

            candidates.sort(key=dist2)

            for d in candidates[:needed]:
                assigned[d] = fid

        # 6) If there are still drones not assigned to any field, assign them to the top-threat field
        remaining = total_drones - len(assigned)
        if remaining > 0:
            top_id = threat_fields[0].id
            cx, cy = ((threat_fields[0].left + threat_fields[0].right) / 2.0,
                      (threat_fields[0].top + threat_fields[0].bottom) / 2.0)
            def dist2_top(d):
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                return dx*dx + dy*dy

            unassigned = [d for d in components if assigned.get(d) is None]
            unassigned.sort(key=dist2_top)
            for d in unassigned[:remaining]:
                assigned[d] = top_id

        # 7) Final: map to groups
        for c in components:
            fid = assigned.get(c, None)
            if fid is not None:
                environment.assign_group(c, f"protecting {fid}")
            else:
                environment.assign_group(c, "idle")