"""Versioned drawing scene shared by recorded replay and future live decoding.

This is the scene boundary, not the AIDL/request/epoch delivery envelope.
"""

MAX_PATHS = 8
MAX_PATH_POINTS = 24
MAX_POINTS = 96
MAX_RADIUS_DM = 2000
STATES = {"active", "idle", "recalculating", "unavailable"}
MODES = {"routing_branches", "map_context", "route_only", "unavailable"}


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def valid_point(point, radius):
    return (isinstance(point, list) and len(point) == 2
            and all(integer(n, -radius, radius) for n in point)
            and point[0] ** 2 + point[1] ** 2 <= radius ** 2)


def validate(scene):
    if not isinstance(scene, dict) or not integer(scene.get("version"), 1, 1):
        return ["unsupported scene version"]
    errors = []
    for key in ("generation", "seq"):
        if not integer(scene.get(key), 0, 1_000_000): errors.append(key)
    if not isinstance(scene.get("session"), str) or not 1 <= len(scene["session"]) <= 64: errors.append("session")
    if scene.get("state") not in STATES: errors.append("state")
    if scene.get("geometryMode") not in MODES: errors.append("geometryMode")
    full_context=scene.get("geometryMode")=="map_context"
    max_paths,max_path_points,max_points=(32,48,512) if full_context else (MAX_PATHS,MAX_PATH_POINTS,MAX_POINTS)
    for key in ("sourceAgeMs", "fixAgeMs"):
        if not integer(scene.get(key), 0, 60_000): errors.append(key)
    # Optional pair. distanceM refers to this route-matched sample, not an
    # already extrapolated position. Legacy scenes keep their measured distance.
    if "progressAgeMs" in scene or "speedDmps" in scene:
        if not integer(scene.get("progressAgeMs"), 0, 60_000): errors.append("progressAgeMs")
        if not integer(scene.get("speedDmps"), 0, 700): errors.append("speedDmps")
    if not integer(scene.get("distanceM"), 0, 1_000_000): errors.append("distanceM")
    for key in ("roadName", "maneuver", "reason"):
        if not isinstance(scene.get(key), str) or len(scene[key]) > 80: errors.append(key)
    radius = scene.get("radiusDm")
    if not integer(radius, 1, MAX_RADIUS_DM): return errors + ["radiusDm"]
    anchors, paths = scene.get("anchors"), scene.get("paths")
    if not isinstance(anchors, list) or len(anchors) > 4: return errors + ["anchors"]
    if not isinstance(paths, list) or len(paths) > max_paths: return errors + ["paths"]
    by_id = {}
    for anchor in anchors:
        if not isinstance(anchor, dict): errors.append("anchor"); continue
        identity = anchor.get("id")
        if not isinstance(identity, str) or not 1 <= len(identity) <= 32 or identity in by_id:
            errors.append("anchor id"); continue
        if not valid_point(anchor.get("point"), radius) or not integer(anchor.get("routeIndex"), 0, 1_000_000):
            errors.append("anchor coordinates/index"); continue
        by_id[identity] = anchor
    ids, total, selected = set(), 0, 0
    for path in paths:
        if not isinstance(path, dict): errors.append("path"); continue
        identity, role, points, links = path.get("id"), path.get("role"), path.get("points"), path.get("anchorRefs")
        if not isinstance(identity, str) or not 1 <= len(identity) <= 32 or identity in ids: errors.append("path id")
        else: ids.add(identity)
        if role not in ("selected", "branch", "context") or (role=="context" and not full_context): errors.append("path role")
        selected += role == "selected"
        if not isinstance(points, list) or not 2 <= len(points) <= max_path_points: errors.append("path point count"); continue
        total += len(points)
        if any(not valid_point(p, radius) for p in points): errors.append("point coordinates")
        if not isinstance(links, list) or (not links and role!="context") or len(links)>4 or (role=="context" and links): errors.append("path anchor refs"); continue
        linked = set()
        for ref in links:
            if not isinstance(ref, list) or len(ref) != 2 or not isinstance(ref[0], str) or ref[0] not in by_id:
                errors.append("unknown anchor ref"); continue
            if ref[0] in linked or not integer(ref[1], 0, len(points)-1): errors.append("anchor point index"); continue
            linked.add(ref[0])
            if points[ref[1]] != by_id[ref[0]]["point"]: errors.append("anchor point mismatch")
        if role == "selected" and linked != set(by_id): errors.append("selected path misses decision anchor")
    if total > max_points: errors.append("total point budget")
    active_geometry = scene.get("state") == "active" and scene.get("geometryMode") != "unavailable"
    if active_geometry and (selected != 1 or not anchors): errors.append("missing selected path/anchor")
    if not active_geometry and (paths or anchors): errors.append("inactive state must clear geometry")
    if scene.get("geometryMode") == "route_only" and any(p.get("role") != "selected" for p in paths): errors.append("route_only contains branches")
    return errors
