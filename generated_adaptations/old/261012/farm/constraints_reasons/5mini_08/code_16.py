from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from typing import Any

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # drone id -> (last_group, consecutive_steps)
        self._prev = {}

    def _center(self, field: Any):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist(self, x1, y1, x2, y2):
        return math.hypot(x1 - x2, y1 - y2)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        total = len(drones)

        # helper for group name
        def protecting_gid(fid):
            return f"protecting {fid}"

        # gather fields with positive threat
        fields_all = list(environment.fields)
        fields = [f for f in fields_all if getattr(f, "threat_level", 0.0) > 0.0]
        centers = {f.id: self._center(f) for f in fields}

        # build drone metadata
        drone_meta = []
        for d in drones:
            did = id(d)
            prev_group, prev_steps = self._prev.get(did, (None, 0))
            loc = getattr(d, "location", None)
            x = getattr(loc, "x", 0.0) if loc is not None else 0.0
            y = getattr(loc, "y", 0.0) if loc is not None else 0.0
            drone_meta.append({
                "obj": d,
                "id": did,
                "x": x,
                "y": y,
                "state": getattr(d, "state", None),
                "target_id": getattr(d, "target_id", None),
                "prev_group": prev_group,
                "prev_steps": prev_steps,
            })

        # final assignment mapping: drone id -> group
        final_assign = {}

        # If no threatened fields: idle everything
        if not fields:
            for dm in drone_meta:
                assigned = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(dm["obj"], assigned)
                last_group, last_steps = self._prev.get(dm["id"], (None, 0))
                if last_group == assigned:
                    self._prev[dm["id"]] = (assigned, last_steps + 1)
                else:
                    self._prev[dm["id"]] = (assigned, 1)
            return

        # helper: distance to field center
        def dist_to_field(dm, fid):
            cx, cy = centers[fid]
            return self._dist(dm["x"], dm["y"], cx, cy)

        # helper: available drones not yet assigned
        def available():
            return [dm for dm in drone_meta if dm["id"] not in final_assign]

        # determine top (most threatened) field and assign its closest drones
        fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        top_field = fields[0]
        top_gid = protecting_gid(top_field.id)
        k_top = int(getattr(top_field, "drones_for_full_protection", 0))
        if k_top > 0 and top_gid in group_ids:
            sorted_all = sorted(drone_meta, key=lambda dm: dist_to_field(dm, top_field.id))
            chosen_top = sorted_all[:min(k_top, len(sorted_all))]
            for dm in chosen_top:
                final_assign[dm["id"]] = top_gid

        # build idle pool: drones not assigned yet and that are idle-like (prev_group == 'idle' or state == 'idle' or no prev)
        def build_idle_pool():
            return [dm for dm in available() if (dm["prev_group"] == "idle" or dm["state"] == "idle" or dm["prev_group"] is None)]

        # For other fields, only keep defenders if they will be part of a full-protection set.
        remaining_fields = [f for f in fields if f.id != top_field.id]
        # process fields in descending threat order
        remaining_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        for f in remaining_fields:
            gid = protecting_gid(f.id)
            if gid not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # collect existing protectors among available drones
            cand = available()
            existing = []
            for dm in cand:
                if dm["prev_group"] == gid:
                    existing.append(dm)
                elif dm["state"] in ("protecting", "moving_to_field") and dm["target_id"] == f.id:
                    existing.append(dm)
            # If we already have enough existing protectors, keep the closest required of them
            if len(existing) >= required:
                existing.sort(key=lambda dm: dist_to_field(dm, f.id))
                keep = existing[:required]
                for dm in keep:
                    final_assign[dm["id"]] = gid
                continue
            # Otherwise, check whether we can fill the gap using idle drones
            idle_pool = build_idle_pool()
            if len(existing) + len(idle_pool) >= required:
                # choose closest existing first, then closest idle drones
                existing.sort(key=lambda dm: dist_to_field(dm, f.id))
                keep_existing = existing  # all existing (fewer than required)
                need = required - len(keep_existing)
                # choose nearest idle from idle_pool
                idle_pool.sort(key=lambda dm: dist_to_field(dm, f.id))
                chosen_idle = idle_pool[:need]
                # assign existing + chosen idle
                for dm in keep_existing:
                    final_assign[dm["id"]] = gid
                for dm in chosen_idle:
                    final_assign[dm["id"]] = gid
                # no need to explicitly remove idle_pool here; available() will reflect final_assign next iteration
            else:
                # Not enough to fully protect: do NOT keep existing (release partial protectors)
                # They will be assigned to idle later.
                continue

        # After considering existing protectors, use remaining idle drones to fully protect additional fields
        idle_pool = build_idle_pool()
        if idle_pool:
            # Try to protect remaining fields by descending threat, using only idle_pool
            other_fields = [f for f in remaining_fields if f.id not in {int(k.split()[-1]) if isinstance(k, str) and k.startswith("protecting ") else None for k in []}]
            # Actually just iterate remaining_fields in order (they are sorted by threat)
            for f in remaining_fields:
                gid = protecting_gid(f.id)
                if gid not in group_ids:
                    continue
                required = int(getattr(f, "drones_for_full_protection", 0))
                if required <= 0:
                    continue
                # count already assigned to this field
                already = sum(1 for did, g in final_assign.items() if g == gid)
                need = required - already
                if need <= 0:
                    continue
                if len(idle_pool) >= need:
                    idle_pool.sort(key=lambda dm: dist_to_field(dm, f.id))
                    chosen = idle_pool[:need]
                    for dm in chosen:
                        final_assign[dm["id"]] = gid
                    # remove chosen from idle_pool
                    idle_pool = [dm for dm in idle_pool if dm["id"] not in final_assign]
                else:
                    # don't partially protect
                    continue

        # Finally, assign any unassigned drones to idle
        for dm in drone_meta:
            if dm["id"] not in final_assign:
                final_assign[dm["id"]] = "idle"

        # Commit assignments and update prev tracking
        for dm in drone_meta:
            obj = dm["obj"]
            did = dm["id"]
            assigned = final_assign.get(did, "idle")
            if assigned not in group_ids:
                assigned = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            environment.assign_group(obj, assigned)
            last_group, last_steps = self._prev.get(did, (None, 0))
            if last_group == assigned:
                self._prev[did] = (assigned, last_steps + 1)
            else:
                self._prev[did] = (assigned, 1)