Reasoning and updated adaptation strategy

Goal
- Further reduce average damage by adopting a more aggressive, arrival-aware, and globally greedy allocation strategy. The focus remains on fully protecting the top-threat field first, but the second phase now assigns remaining drones to the best overall field using a composite scoring function that considers threat, remaining need, arrival time, distance, and per-drone memory. This reduces protection latency for the top field while efficiently distributing the rest of the drones.

Key ideas
- Arrival-time aware scoring: drones already heading to a field or already protecting it have zero arrival time; others are penalized by their estimated arrival.
- Memory bias: drones with history protecting a field get a small boost when evaluating that field, helping stability without stalling progress to top-field protection.
- Phase 1: Guarantee full protection for the top-threat field using the closest drones (with memory bias).
- Phase 2: Greedy, global allocation of remaining drones to other threatening fields by maximizing a composite score that blends threat level, remaining need, arrival, distance, and memory.
- Phase 3: If fewer than half of the drones are protecting, opportunistically fill to half using the same scoring approach.
- Stability: memory persists across steps to reduce unnecessary churn, but is used as a soft bias, never preventing timely protection of the top field.

Code
- The following Python code implements the enhanced strategy as a single class SmartFarmAdaptation that derives from FarmAdaptation and uses environment.assign_group to set groups.

```py
from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persist across steps: map drone_id -> last_protected_field_id (string) or None
        self._last_target_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Gather threatened fields (threat_level > 0)
        fields = list(getattr(environment, "fields", []))
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If nothing is threatened, idle all drones and reset memory
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            for d in components:
                self._last_target_by_drone[id(d)] = None
            return

        # 2) Compute field centers for distance calculations
        field_centers = {}
        for f in threatened_fields:
            cx = (f.left + f.right) / 2.0
            cy = (f.top  + f.bottom) / 2.0
            field_centers[f.id] = (cx, cy)

        # 3) Helper: determine current group for a drone (considers moving_to_field as protection)
        def current_group(d):
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            if st in ("protecting", "moving_to_field") and tid is not None:
                return f"protecting {tid}"
            return "idle"

        # 4) Start with the current assignment as the baseline
        final_group = {d: current_group(d) for d in components}

        # 5) Sort threatened fields by threat descending
        threatened_sorted = sorted(
            threatened_fields,
            key=lambda ff: getattr(ff, "threat_level", 0),
            reverse=True
        )

        # Helper to fill a field to full protection with prioritized candidates (Phase 1)
        def fill_field_to_full(field):
            field_id = field.id
            grp = f"protecting {field_id}"
            current_protectors = sum(1 for d in components if final_group.get(d) == grp)
            needed = int(getattr(field, "drones_for_full_protection", 0)) - current_protectors
            if needed <= 0:
                return
            cx, cy = field_centers[field_id]

            # Build candidates not currently protecting this field
            candidates = []
            for d in components:
                if final_group.get(d) == grp:
                    continue
                loc = getattr(d, "location", None)
                if loc is None:
                    dist = float("inf")
                else:
                    dx = getattr(loc, "x", 0.0) - cx
                    dy = getattr(loc, "y", 0.0) - cy
                    dist = sqrt(dx*dx + dy*dy)
                # arrival time to this field
                if getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == field_id:
                    arrival = 0.0
                else:
                    arrival = dist / 2.0  # speed = 2
                last = (self._last_target_by_drone.get(id(d)) == field_id)
                mem = 1.0 if last else 0.0
                threat = getattr(field, "threat_level", 0.0)
                score = threat * needed + mem - arrival * 0.9 - dist * 0.01
                candidates.append((score, arrival, dist, d, last))
            candidates.sort(key=lambda t: (-t[0], t[1], t[2]))
            for _, _, _, d, _ in candidates[:max(0, needed)]:
                final_group[d] = grp

        # Phase 1: top field
        top_field = threatened_sorted[0]
        fill_field_to_full(top_field)

        # Phase 2: Greedy distribution of remaining drones to best fields
        total = len(components)
        half = (total + 1) // 2

        # Compute current needs after Phase 1
        needs = {}
        for f in threatened_sorted[1:]:
            current = sum(1 for d in components if final_group.get(d) == f"protecting {f.id}")
            need = int(getattr(f, "drones_for_full_protection", 0)) - current
            if need > 0:
                needs[f.id] = need
        # While there are needs, perform a greedy, global allocation
        field_by_id = {f.id: f for f in threatened_sorted}
        while needs:
            best_pair = None
            best_score = -1e9

            # Evaluate best (drone, field) pair across all drones
            for d in components:
                current = final_group.get(d)
                current_field_id = current.split(" ", 1)[1] if isinstance(current, str) and current.startswith("protecting ") else None

                best_for_drone = None
                best_for_score = -1e9

                for fid, need in list(needs.items()):
                    if need <= 0:
                        continue
                    f = field_by_id[fid]
                    cx, cy = field_centers[fid]

                    loc = getattr(d, "location", None)
                    dist = float("inf") if loc is None else sqrt((getattr(loc, "x", 0.0) - cx) ** 2 + (getattr(loc, "y", 0.0) - cy) ** 2)
                    arrival = 0.0 if getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == fid else dist / 2.0
                    mem = 1.0 if (self._last_target_by_drone.get(id(d)) == fid) else 0.0
                    threat = getattr(f, "threat_level", 0.0)
                    need_val = need
                    score = threat * need_val + mem - arrival * 0.9 - dist * 0.01

                    if score > best_for_score:
                        best_for_score = score
                        best_for_drone = (d, fid)

                if best_for_drone is not None:
                    d_best, fid_best = best_for_drone
                    if current_field_id == fid_best:
                        # If drone already targets this field, skip for this iteration
                        continue
                    if best_for_score > best_score:
                        best_score = best_for_score
                        best_pair = (d_best, fid_best)

            if best_pair is None:
                break

            d_sel, fid_sel = best_pair
            final_group[d_sel] = f"protecting {fid_sel}"
            needs[fid_sel] -= 1
            if needs[fid_sel] <= 0:
                del needs[fid_sel]

            # Update best_score for next iteration
            # (Loop will recompute in next iteration)

        # Phase 3: Ensure at least half of drones are protecting if possible
        current_protectors = sum(1 for d in components if final_group.get(d, "idle").startswith("protecting "))
        if current_protectors < half:
            # Recompute needs
            needs = {}
            for f in threatened_sorted:
                fid = f.id
                current = sum(1 for d in components if final_group.get(d) == f"protecting {fid}")
                rem = int(getattr(f, "drones_for_full_protection", 0)) - current
                if rem > 0:
                    needs[fid] = rem
            # Greedily fill to reach half
            while needs and current_protectors < half:
                best_pair = None
                best_score = -1e9
                for d in components:
                    current = final_group.get(d)
                    current_field_id = current.split(" ", 1)[1] if isinstance(current, str) and current.startswith("protecting ") else None
                    best_for_drone = None
                    best_for_score = -1e9

                    for fid, need in list(needs.items()):
                        if need <= 0:
                            continue
                        f = field_by_id[fid]
                        cx, cy = field_centers[fid]
                        loc = getattr(d, "location", None)
                        dist = float("inf") if loc is None else sqrt((getattr(loc, "x", 0.0) - cx) ** 2 + (getattr(loc, "y", 0.0) - cy) ** 2)
                        arrival = 0.0 if getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == fid else dist / 2.0
                        mem = 1.0 if (self._last_target_by_drone.get(id(d)) == fid) else 0.0
                        threat = getattr(f, "threat_level", 0.0)
                        need_val = need
                        score = threat * need_val + mem - arrival * 0.9 - dist * 0.01
                        if score > best_for_score:
                            best_for_score = score
                            best_for_drone = (d, fid)

                    if best_for_drone is not None:
                        d_best, fid_best = best_for_drone
                        if current_field_id == fid_best:
                            continue
                        if best_for_score > best_score:
                            best_score = best_for_score
                            best_pair = (d_best, fid_best)

                if best_pair is None:
                    break

                d_sel, fid_sel = best_pair
                final_group[d_sel] = f"protecting {fid_sel}"
                current_protectors += 1
                needs[fid_sel] = max(0, needs.get(fid_sel, 0) - 1)
                if current_protectors >= half:
                    break

        # 4) Step memory update
        for d in components:
            g = final_group.get(d, "idle")
            if isinstance(g, str) and g.startswith("protecting "):
                field_id = g.split(" ", 1)[1]
                self._last_target_by_drone[id(d)] = field_id
            else:
                self._last_target_by_drone[id(d)] = None

        # 5) Final assignment to environment
        for d in components:
            grp = final_group.get(d, "idle")
            environment.assign_group(d, grp)
```