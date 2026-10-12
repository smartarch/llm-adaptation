Reasoning and updated adaptation strategy

What we learned from the last runs
- The top-field protection remains critical, but now we can push protection earlier by explicitly considering arrival times for all candidate drones.
- Memory continues to help stability, but we should not let it overly constrain progress to fully protect the top field.
- A more global, score-driven second phase can better distribute remaining drones to other threatened fields in a way that maximizes the overall protection effect while still honoring the “full protection for the top field” priority.
- We should implement a true greedy, multi-field allocation for the secondary phase that uses per-drone best-field scoring and updates the needs of each field as drones are allocated. This reduces unnecessary churn and improves utilization.

Key improvements in this version
- Arrival-time aware candidate scoring for the top field: still prioritize closest drones, but explicitly factor in arrival times to reduce protection latency.
- A two-phase allocation with a stronger, global second phase:
  - Phase 1: fully protect the top-threat field using the closest drones with memory bias.
  - Phase 2: iteratively assign remaining drones to the best field among those still needing protection, based on a composite score that includes: field threat, remaining need, drone arrival time, distance, and memory (favor drones that previously protected that field).
- After the Phase 2 greedy pass, if we still don’t reach half the drones protecting, perform a final opportunistic pass to reach the half-threshold when feasible.
- Stability: memory is still used to bias choices toward the previous target, but not at the cost of timely top-field protection.

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

        # Helper to fill a field to full protection with prioritized candidates
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
                last_match = (self._last_target_by_drone.get(id(d)) == field_id)
                # Prefer drones that previously protected this field
                candidates.append((0 if last_match else 1, arrival, dist, d))
            candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            for _, _, _, d in candidates[:max(0, needed)]:
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
            need = int(getattr(f, "drones_for_full_protection", 0)) - sum(
                1 for d in components if final_group.get(d) == f"protecting {f.id}"
            )
            if need > 0:
                needs[f.id] = need

        # If there are needs, perform a greedy assignment for remaining drones
        # We will iteratively assign the best drone to the best field until needs are filled
        # or no viable drone remains.
        # Build a quick lookup for field center and threat level
        field_by_id = {f.id: f for f in threatened_sorted}
        changed = True
        while needs and changed:
            changed = False
            best_score = None
            best_pair = None  # (drone, field_id)

            # Precompute available drones that are not already assigned to the target field needing protection
            for d in components:
                current = final_group.get(d, "idle")
                if isinstance(current, str) and current.startswith("protecting "):
                    current_field_id = current.split(" ", 1)[1]
                else:
                    current_field_id = None

                # If all needs are zero, break
                if not needs:
                    break

                # Evaluate best field for this drone
                best_for_drone = None
                best_for_score = -1e9

                # Consider each field that still needs drones
                for fid, need in list(needs.items()):
                    f = field_by_id[fid]
                    cx, cy = field_centers[fid]

                    loc = getattr(d, "location", None)
                    if loc is None:
                        dist = float("inf")
                    else:
                        dx = getattr(loc, "x", 0.0) - cx
                        dy = getattr(loc, "y", 0.0) - cy
                        dist = sqrt(dx*dx + dy*dy)

                    # arrival
                    if getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == fid:
                        arrival = 0.0
                    else:
                        arrival = dist / 2.0

                    # memory bias
                    mem = 0.0 if (self._last_target_by_drone.get(id(d)) == fid) else 1.0

                    threat = getattr(f, "threat_level", 0.0)
                    # Composite score: prioritize higher threat and higher need, then faster arrival and memory
                    score = (threat * need) - (arrival * 0.8) - (dist * 0.02) + (0.3 * (1.0 - mem))  # mem bonus

                    if score > best_for_score:
                        best_for_score = score
                        best_for_drone = fid

                if best_for_drone is None:
                    continue

                # If this drone already protects the best field and it's the same, skip
                if current_field_id == best_for_drone:
                    continue

                # Update best overall
                if best_for_score > (best_score if best_score is not None else -1e9):
                    best_score = best_for_score
                    best_pair = (d, best_for_drone)

            if best_pair is None:
                break

            d_sel, field_id = best_pair
            # Assign this drone to the selected field
            final_group[d_sel] = f"protecting {field_id}"
            needs[field_id] -= 1
            if needs[field_id] <= 0:
                del needs[field_id]
            changed = True

        # After Phase 2, ensure at least half of drones are protecting if possible
        current_protectors = sum(1 for d in components if final_group.get(d, "idle").startswith("protecting "))
        if current_protectors < half:
            # Opportunistic assignments to highest-threat fields still needing protection
            # Recompute needs (in case some got filled)
            needs = {}
            for f in threatened_sorted:
                fid = f.id
                if all(final_group.get(d) != fid for d in components):
                    # If no one protecting this field yet, it needs full protection
                    current = 0
                else:
                    current = sum(1 for d in components if final_group.get(d) == f"protecting {fid}")
                remaining = int(getattr(f, "drones_for_full_protection", 0)) - current
                if remaining > 0:
                    needs[fid] = remaining

            # Simple greedy fill based on best score
            for fid, need in sorted(needs.items(), key=lambda kv: field_by_id[kv[0]].threat_level, reverse=True):
                if current_protectors >= half:
                    break
                f = field_by_id[fid]
                cx, cy = field_centers[fid]
                grp = f"protecting {fid}"
                # Build candidates
                candidates = []
                for d in components:
                    if final_group.get(d) == grp:
                        continue
                    loc = getattr(d, "location", None)
                    dist = float("inf") if loc is None else sqrt((getattr(loc, "x", 0.0) - cx)**2 + (getattr(loc, "y", 0.0) - cy)**2)
                    arrival = 0.0 if (getattr(d, "state", None) in ("moving_to_field", "protecting") and getattr(d, "target_id", None) == fid) else dist / 2.0
                    mem = 0.0 if (self._last_target_by_drone.get(id(d)) == fid) else 1.0
                    score = getattr(f, "threat_level", 0.0) * need - arrival * 0.8 - dist * 0.02 + (0.3 * (1.0 - mem))
                    candidates.append((score, d, dist, arrival, mem))
                candidates.sort(key=lambda t: (-t[0], t[2], t[3]))
                if not candidates:
                    continue
                # pick best candidate
                score, dsel, dist, arrival, mem = candidates[0]
                final_group[dsel] = grp
                current_protectors += 1
                if current_protectors >= half:
                    break

        # 9) Step 4: Update memory of last target per drone
        for d in components:
            g = final_group.get(d, "idle")
            if isinstance(g, str) and g.startswith("protecting "):
                field_id = g.split(" ", 1)[1]
                self._last_target_by_drone[id(d)] = field_id
            else:
                self._last_target_by_drone[id(d)] = None

        # 10) Final assignment to environment
        for d in components:
            grp = final_group.get(d, "idle")
            environment.assign_group(d, grp)
```