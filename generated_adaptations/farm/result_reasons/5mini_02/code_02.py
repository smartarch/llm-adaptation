from typing import Dict, Tuple, List
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # prev_groups maps component_id -> (group_id, duration_steps)
        self.prev_groups: Dict[int, Tuple[str, int]] = {}

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, comp, field):
        cx, cy = self._field_center(field)
        dx = comp.location.x - cx
        dy = comp.location.y - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build list of fields with threat > 0, sorted descending by threat_level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)

        total_drones = len(components)
        # initialize per-component info
        comp_infos = []
        for comp in components:
            cid = id(comp)
            # derive previous group from internal memory or from current state/target (observed)
            if cid in self.prev_groups:
                prev_group, prev_dur = self.prev_groups[cid]
            else:
                # infer from observed state/target_id
                if getattr(comp, "state", None) in ("protecting", "moving_to_field") and getattr(comp, "target_id", None):
                    prev_group = f"protecting {comp.target_id}"
                else:
                    prev_group = "idle"
                prev_dur = 0
            comp_infos.append({
                "comp": comp,
                "cid": cid,
                "prev_group": prev_group,
                "prev_dur": prev_dur,
                "assigned": None,  # group to assign
            })

        # Helper to pick k best drones for a given field using switch cost + distance
        def pick_drones_for_field(field, k, available_infos):
            picks = []
            for info in available_infos:
                comp = info["comp"]
                prev = info["prev_group"]
                # compute switch cost:
                # 0 if already assigned (prev) to this field
                # 1 if idle or moving to this field (i.e., prev is 'idle' or same field)
                # 2 if switching from another field
                target_group = f"protecting {field.id}"
                if prev == target_group:
                    switch_cost = 0
                elif prev == "idle":
                    switch_cost = 1
                elif prev.startswith("protecting ") and prev != target_group:
                    switch_cost = 2
                else:
                    # other states
                    switch_cost = 1
                dist = self._distance(comp, field)
                picks.append((switch_cost, dist, info))
            # sort by switch_cost then distance
            picks.sort(key=lambda t: (t[0], t[1]))
            selected = [t[2] for t in picks[:k]]
            return selected

        # Assignment plan:
        # 1) Always fully protect the top field
        # 2) Try to fully protect subsequent fields while possible (descending threat)
        # 3) If after that fewer than half drones are protecting, assign remaining drones to partially protect next best field (fallback)
        assignments = {}  # cid -> group_id

        # available pool: those not yet assigned
        available = list(comp_infos)

        # Protect fields fully when possible, starting with highest threat.
        protected_fields = []
        for i, field in enumerate(fields):
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            # For the top-most field (i == 0) we must fully protect it.
            # For others we will protect only if we can satisfy full protection.
            # Count currently assigned to this field from prev (prefer to keep them)
            # But selection function will prefer those anyway.
            if len(available) < required:
                # Not enough remaining drones to fully protect this field
                # If this is the top field (i==0), we still try and assign as many closest as possible (should rarely happen).
                if i == 0:
                    # pick up to len(available)
                    picks = pick_drones_for_field(field, len(available), available)
                    for info in picks:
                        assignments[info["cid"]] = f"protecting {field.id}"
                        info["assigned"] = f"protecting {field.id}"
                        available.remove(info)
                    protected_fields.append(field)
                    # can't protect others fully
                    break
                else:
                    # skip full protection for this field
                    continue
            else:
                # select required drones
                picks = pick_drones_for_field(field, required, available)
                for info in picks:
                    assignments[info["cid"]] = f"protecting {field.id}"
                    info["assigned"] = f"protecting {field.id}"
                    available.remove(info)
                protected_fields.append(field)
                # continue to next field

        # Count how many drones are protecting now
        protecting_count = sum(1 for v in assignments.values() if v != "idle")

        # If protecting_count < half of total_drones, try a fallback: partially protect the next best field
        half_needed = math.ceil(total_drones / 2)
        if protecting_count < half_needed and fields:
            # find next best field not already protected (by id) with threat>0
            protected_ids = {f.id for f in protected_fields}
            remaining_fields = [f for f in fields if f.id not in protected_ids]
            if remaining_fields:
                next_field = remaining_fields[0]
                # assign all remaining drones to this field (but do not exceed its drones_for_full_protection)
                max_assign = int(getattr(next_field, "drones_for_full_protection", 0))
                if max_assign <= 0:
                    # if no number specified, just use remaining to reach half
                    need = half_needed - protecting_count
                    assign_count = min(len(available), need)
                else:
                    need = half_needed - protecting_count
                    # assign at most max_assign, and not more than available
                    assign_count = min(len(available), max_assign, max(need, 0))
                    if assign_count == 0 and len(available) > 0:
                        # if still none assigned (maybe need==0), but we want to reduce idles, assign at least 1 up to available
                        assign_count = min(len(available), max_assign)
                if assign_count > 0:
                    picks = pick_drones_for_field(next_field, assign_count, available)
                    for info in picks:
                        assignments[info["cid"]] = f"protecting {next_field.id}"
                        info["assigned"] = f"protecting {next_field.id}"
                        available.remove(info)
                    protecting_count = sum(1 for v in assignments.values() if v != "idle")

        # Any remaining drones -> idle
        for info in available:
            assignments[info["cid"]] = "idle"
            info["assigned"] = "idle"

        # Finally, ensure top field is protected (fallback if earlier logic skipped it)
        # If top field exists and we somehow failed to allocate any drones to it, force reallocation from idle drones (should not happen)
        if fields:
            top_field = fields[0]
            top_group = f"protecting {top_field.id}"
            top_assigned = sum(1 for g in assignments.values() if g == top_group)
            required_top = int(getattr(top_field, "drones_for_full_protection", 0))
            if required_top > top_assigned:
                need = required_top - top_assigned
                # find drones currently idle or assigned to lower-priority fields, prefer idle
                idle_candidates = [info for info in comp_infos if assignments.get(info["cid"]) == "idle"]
                other_candidates = [info for info in comp_infos if assignments.get(info["cid"]) != top_group and assignments.get(info["cid"]) != "idle"]
                candidates = idle_candidates + other_candidates
                picks = pick_drones_for_field(top_field, min(need, len(candidates)), candidates)
                for info in picks:
                    assignments[info["cid"]] = top_group
                    info["assigned"] = top_group

        # Apply assignments via environment.assign_group and update prev_groups tracking
        for info in comp_infos:
            cid = info["cid"]
            comp = info["comp"]
            assigned_group = assignments.get(cid, "idle")
            # ensure assigned_group is among group_ids; if not, fallback to 'idle'
            if assigned_group not in group_ids:
                assigned_group = "idle"
            # call environment.assign_group
            environment.assign_group(comp, assigned_group)
            # update prev_groups duration
            prev_group, prev_dur = self.prev_groups.get(cid, (info["prev_group"], info["prev_dur"]))
            if prev_group == assigned_group:
                new_dur = prev_dur + 1
            else:
                new_dur = 1
            self.prev_groups[cid] = (assigned_group, new_dur)