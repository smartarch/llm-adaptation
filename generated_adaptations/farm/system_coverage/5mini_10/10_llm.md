Reasoning and adaptation strategy

What I'll change
- In the last version I only counted drones in state "protecting" as already contributing to the target field. Drones that are already moving_to_field with target == target field are also committed and will soon help protect that field — it's beneficial to treat them as part of the target assignment so we don't reassign them away and so we count them when deciding how many extra drones are needed.
- So I will:
  - Treat both protecting and moving_to_field (when target_id == target) as pre-assigned to the target.
  - Lock only drones that are currently protecting fields that were initially already fully protected (same as before). Moving-to-target drones are not locked against reassignment except that we will treat them as selected for the target (we will assign them to the target group).
  - Prefer drones that are already protecting or already moving to the target when choosing additional drones.
  - Use distance to nearest point on the field rectangle as the travel-time proxy (same as before).
- This should reduce wasted reassignments and speed up reaching full protection on the top-threat field, reducing damage.

Strategy summary
1. Find fields with threat_level > 0 and pick the one with maximum threat (tie-break by id).
2. Mark drones that are protecting fully-protected fields as locked (cannot reassign).
3. Consider drones with state "protecting" OR state "moving_to_field" and target == target field as already committed to the target.
4. If the number of committed drones >= drones_for_full_protection, keep them on the target (and keep locked drones on their fields); everyone else -> idle.
5. Otherwise, pick the nearest available drones (excluding locked drones and excluding already-committed drones) to reach the required count; prefer those moving_to_field->target and those already protecting target.
6. Assign chosen drones to "protecting {target_id}", locked drones stay protecting their fields, others -> idle.

Code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy: treat both 'protecting' and 'moving_to_field' (when targeting the chosen field)
        as committed to that field, to avoid reassigning in-transit drones and to reduce time to full protection.
        """
        # Helper: squared distance from point (x,y) to rectangle (0 if inside)
        def dist2_to_rect(x, y, field):
            dx = 0.0
            if x < field.left:
                dx = field.left - x
            elif x > field.right:
                dx = x - field.right
            dy = 0.0
            if y < field.top:
                dy = field.top - y
            elif y > field.bottom:
                dy = y - field.bottom
            return dx * dx + dy * dy

        # Idle fallback group
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Collect threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Choose target: highest threat, tie-break by id
        target_field = max(threatened_fields, key=lambda f: (f.threat_level, f.id))
        target_id = target_field.id
        target_group = f"protecting {target_id}"

        # If protecting group not available, idle all
        if target_group not in group_ids:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Build protecting counts and lists for threatened fields (only state == "protecting")
        protecting_counts = {f.id: 0 for f in threatened_fields}
        protecting_drones = {f.id: [] for f in threatened_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in protecting_counts:
                    protecting_counts[tid] += 1
                    protecting_drones[tid].append(d)

        # Identify initially fully protected fields and lock their protecting drones
        fully_protected_initial = set()
        for f in threatened_fields:
            cnt = protecting_counts.get(f.id, 0)
            if cnt >= int(f.drones_for_full_protection):
                fully_protected_initial.add(f.id)

        locked_ids = set()
        for fid in fully_protected_initial:
            for d in protecting_drones.get(fid, []):
                locked_ids.add(id(d))

        # Determine drones already committed to the target:
        # include both state "protecting" with target==target and state "moving_to_field" with target==target
        committed_to_target = []
        for d in components:
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            if tid == target_id and (st == "protecting" or st == "moving_to_field"):
                committed_to_target.append(d)

        committed_ids = {id(d) for d in committed_to_target}
        already_committed_count = len(committed_to_target)

        required_total = int(target_field.drones_for_full_protection)

        # If already enough committed (protecting + moving), keep them; keep locked drones; others idle
        if already_committed_count >= required_total:
            for d in components:
                did = id(d)
                if did in committed_ids:
                    # assign to target protecting group (moving-to-target drones will remain targeting it)
                    environment.assign_group(d, target_group)
                elif getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fully_protected_initial:
                    # keep locked protectors on their fields
                    grp = f"protecting {d.target_id}"
                    environment.assign_group(d, grp if grp in group_ids else idle_group)
                else:
                    environment.assign_group(d, idle_group)
            return

        # Need additional drones
        need = max(0, required_total - already_committed_count)

        # Candidate drones: all drones excluding locked ones and excluding already committed ones
        candidates = [d for d in components if id(d) not in locked_ids and id(d) not in committed_ids]

        # Sort candidates by:
        # 1) prefer drones moving_to_field toward target (they're already headed there),
        # 2) prefer drones currently protecting the target (shouldn't be here but safe),
        # 3) distance to rectangle,
        # 4) id for determinism
        def candidate_key(d):
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            moving_pref = 0 if (st == "moving_to_field" and tid == target_id) else 1
            protecting_pref = 0 if (st == "protecting" and tid == target_id) else 1
            loc = getattr(d, "location", None)
            if loc is None:
                dist2 = float("inf")
            else:
                dist2 = dist2_to_rect(getattr(loc, "x", 0), getattr(loc, "y", 0), target_field)
            return (moving_pref, protecting_pref, dist2, id(d))

        candidates.sort(key=candidate_key)

        selected = candidates[:need]
        selected_ids = {id(d) for d in selected}
        final_selected_ids = committed_ids | selected_ids

        # Assign groups: selected/committed -> target, locked protectors remain, others idle
        for d in components:
            did = id(d)
            if did in final_selected_ids:
                environment.assign_group(d, target_group)
            elif getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fully_protected_initial:
                grp = f"protecting {d.target_id}"
                environment.assign_group(d, grp if grp in group_ids else idle_group)
            else:
                environment.assign_group(d, idle_group)
```