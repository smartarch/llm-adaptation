from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        def valid_group(name):
            return name in group_ids

        comps = list(components)
        n = len(comps)

        # Build list of threatened fields sorted by threat desc, tie-break by id
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # No threats: assign all drones to idle
            for c in comps:
                environment.assign_group(c, "idle")
            return

        threatened.sort(key=lambda f: (f.threat_level, str(f.id)), reverse=True)

        # Prepare available drone indices
        available = set(range(n))
        # Mapping of drone index -> field_id to assign
        assignments = {}

        # Precompute drone locations for distance calculations
        locs = []
        for c in comps:
            lx = getattr(c.location, "x", 0.0)
            ly = getattr(c.location, "y", 0.0)
            locs.append((lx, ly))

        # Helper to compute distance to field center
        def dist_to_field(idx, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            lx, ly = locs[idx]
            return math.hypot(lx - cx, ly - cy)

        # Iterate fields by priority and try to fully protect as many as possible
        for idx_field, field in enumerate(threatened):
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue

            # Find current drones that are already protecting this field and still available
            current_protecting = [i for i in list(available)
                                  if getattr(comps[i], "state", None) == "protecting"
                                  and getattr(comps[i], "target_id", None) == field.id]

            # If this is the highest-threat field (first in list), we must try to protect it.
            if idx_field == 0:
                # Need to ensure as many as possible up to required (if not enough drones exist, allocate all available)
                already = len(current_protecting)
                need = max(0, required - already)
                # Choose closest from available excluding those already counted
                candidates = [i for i in available if i not in current_protecting]
                candidates.sort(key=lambda i: dist_to_field(i, field))
                chosen = current_protecting[:]  # keep the existing ones
                for i in candidates:
                    if need <= 0:
                        break
                    chosen.append(i)
                    need -= 1
                # Assign chosen (may be fewer than required if not enough drones)
                for i in chosen:
                    assignments[i] = field.id
                    if i in available:
                        available.remove(i)
            else:
                # For lower-priority fields: only fully protect if enough available drones exist to reach full protection
                already = len(current_protecting)
                need = max(0, required - already)
                # Count of other available drones that could be used (exclude those currently protecting this field)
                candidate_pool = [i for i in available if i not in current_protecting]
                if len(candidate_pool) >= need and (already > 0 or need > 0):
                    # We can fully protect this field: pick the closest candidates
                    candidate_pool.sort(key=lambda i: dist_to_field(i, field))
                    chosen = current_protecting[:]
                    take = need
                    for i in candidate_pool:
                        if take <= 0:
                            break
                        chosen.append(i)
                        take -= 1
                    for i in chosen:
                        assignments[i] = field.id
                        if i in available:
                            available.remove(i)
                else:
                    # Do not partially protect this field: leave its current protecting drones available to be reassigned
                    # (they remain in 'available' for possible use on higher-priority fields)
                    continue

        # After field allocations, assign groups accordingly
        for i, c in enumerate(comps):
            if i in assignments:
                grp = f"protecting {assignments[i]}"
                if not valid_group(grp):
                    grp = "idle"
                environment.assign_group(c, grp)
            else:
                # Not assigned to any field: idle
                environment.assign_group(c, "idle")