from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        drones = list(components)
        total_drones = len(drones)
        speed = 2.0

        # Helpers
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist(drone, x, y):
            dx = getattr(drone.location, "x", 0) - x
            dy = getattr(drone.location, "y", 0) - y
            return math.hypot(dx, dy)

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            # No threats -> all idle
            for d in drones:
                environment.assign_group(d, "idle")
            return

        # Minimum protecting drones desired
        min_protect = ceil(total_drones / 2.0)

        # Sort fields by descending threat, tie-break by id for determinism
        threatened.sort(key=lambda f: (f.threat_level, f.id), reverse=True)

        # Initialize assignment mapping: keep current protectors assigned to their protecting group
        assigned = {}
        for d in drones:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                assigned[d] = f"protecting {d.target_id}"
            else:
                assigned[d] = None

        # Prepare field info structures
        field_info = {}
        for f in threatened:
            required = int(getattr(f, "drones_for_full_protection", 0))
            grp = f"protecting {f.id}"
            current_assigned = [d for d, g in assigned.items() if g == grp]
            remaining_need = max(0, required - len(current_assigned))
            # marginal per drone (approximate) - avoid divide by zero
            marginal = (getattr(f, "threat_level", 0) / max(1, required)) if required > 0 else getattr(f, "threat_level", 0)
            center = center_of(f)
            field_info[f.id] = {
                "field": f,
                "group": grp,
                "required": required,
                "current": current_assigned[:],  # list
                "remaining": remaining_need,
                "marginal": marginal,
                "center": center
            }

        # Utility to count total protecting now (based on assigned mapping)
        def total_protecting_count():
            return sum(1 for g in assigned.values() if g is not None)

        # Build list of unassigned drones (not currently protecting)
        unassigned_drones = [d for d, g in assigned.items() if g is None]

        # Build candidate scores: for each unassigned drone & each field with remaining need > 0, compute score = marginal / (1 + travel_time)
        candidates = []
        for d in unassigned_drones:
            for fid, info in field_info.items():
                if info["remaining"] <= 0:
                    continue
                cx, cy = info["center"]
                distance = dist(d, cx, cy)
                travel_time = distance / speed
                # Score emphasises marginal benefit and proximity; (1 + travel_time) prevents division by zero
                score = info["marginal"] / (1.0 + travel_time)
                # Slightly boost score if drone is already moving to that field (less effective travel)
                if getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == fid:
                    score *= 1.15
                candidates.append((score, d, fid, distance))

        # Greedy assign: sort candidates by score descending and allocate while respecting remaining needs and min_protect
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Track which drones we have assigned this round to avoid double-assign
        newly_assigned = set()
        for score, d, fid, distance in candidates:
            if assigned[d] is not None:
                continue  # already assigned by earlier step
            info = field_info[fid]
            if info["remaining"] <= 0:
                continue
            # If assigning this drone would exceed min_protect goal unnecessarily, allow but we try to stop once goal reached
            assigned[d] = info["group"]
            newly_assigned.add(d)
            info["remaining"] -= 1
            info["current"].append(d)
            if total_protecting_count() >= min_protect:
                break

        # After exhausting candidates, if we still haven't reached min_protect, consider stealing minimally
        if total_protecting_count() < min_protect:
            need = min_protect - total_protecting_count()
            # Build a list of stealable drones: currently protecting drones (assigned) but prefer those protecting low-threat fields
            steal_pool = []
            for fid, info in field_info.items():
                # for each protector assigned to this field, consider it for stealing (but prefer fields with low threat and those with surplus)
                src_threat = getattr(info["field"], "threat_level", 0)
                for protector in info["current"]:
                    # Do not consider a protector that is the only protector of its field if that field had required > 0 and was exactly satisfied
                    # (try to preserve full protections). If field.required > len(info["current"]) - 1 then stealing would break it.
                    if info["required"] > 0 and (len(info["current"]) - 1) < info["required"]:
                        # stealing would break full protection; still allow if source threat is very low relative to others and we must reach min_protect
                        steal_costly = True
                    else:
                        steal_costly = False
                    steal_pool.append((src_threat, steal_costly, protector, fid))
            # Sort steal pool by src_threat ascending, prefer cheap steals (not costly)
            steal_pool.sort(key=lambda x: (x[1], x[0]))  # non-costly before costly, then lower threat first
            # Try to steal until need satisfied, but avoid stealing from fields with higher threat than the best target field
            # Determine best target fields by marginal descending
            targets_by_marginal = sorted(field_info.values(), key=lambda it: (it["marginal"], getattr(it["field"], "threat_level", 0)), reverse=True)
            target_fids = [it["field"].id for it in targets_by_marginal if it["remaining"] > 0]
            # If no remaining needs, still allow stealing to assign to highest-marginal fields (they will become partially protected)
            if not target_fids:
                target_fids = [it["field"].id for it in targets_by_marginal]
            steal_idx = 0
            for src_threat, steal_costly, protector, src_fid in steal_pool:
                if need <= 0:
                    break
                # Find best target that's not the source field
                chosen_target = None
                for tfid in target_fids:
                    if tfid != src_fid:
                        chosen_target = tfid
                        break
                if chosen_target is None:
                    break
                # Simple policy: only steal if source threat <= chosen target's threat (avoid making worse trade)
                src_field = next((it["field"] for it in field_info.values() if it["field"].id == src_fid), None)
                tgt_info = field_info.get(chosen_target)
                if src_field and tgt_info:
                    if getattr(src_field, "threat_level", 0) > getattr(tgt_info["field"], "threat_level", 0) and not steal_costly:
                        # don't steal from a higher-threat source unless it was already surplus (steal_costly True means we already noted it's costly)
                        continue
                # perform steal
                # remove protector from its current list
                if protector in field_info[src_fid]["current"]:
                    field_info[src_fid]["current"].remove(protector)
                # update required/remaining appropriately: if we removed a protector that was counted toward required, increment remaining on source
                if field_info[src_fid]["required"] > 0:
                    # if after removal, we have fewer than required, increase remaining
                    if len(field_info[src_fid]["current"]) < field_info[src_fid]["required"]:
                        field_info[src_fid]["remaining"] = field_info[src_fid]["required"] - len(field_info[src_fid]["current"])
                # assign protector to new target
                assigned[protector] = field_info[chosen_target]["group"]
                field_info[chosen_target]["current"].append(protector)
                # if this target had remaining > 0, reduce it
                if field_info[chosen_target]["remaining"] > 0:
                    field_info[chosen_target]["remaining"] -= 1
                need -= 1

        # Final pass: if there are still unassigned drones (not protecting), set them idle
        for d in drones:
            final_group = assigned[d]
            if final_group is None:
                environment.assign_group(d, "idle")
            else:
                environment.assign_group(d, final_group)