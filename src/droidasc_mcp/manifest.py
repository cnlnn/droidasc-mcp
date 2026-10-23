"""Manifest declarations and conservative, provenance-bearing permission inheritance."""

from __future__ import annotations

ANDROID = "{http://schemas.android.com/apk/res/android}"
COMPONENTS = {"activity", "activity-alias", "service", "receiver", "provider"}


def attributes(element):
    return dict(element.attrib) if element is not None else {}


def attr(element, name):
    return element.get(ANDROID + name) if element is not None else None


def boolean(value, default=None):
    if value is None:
        return default
    if value.lower() in {"true", "1", "0xffffffff"}:
        return True
    if value.lower() in {"false", "0", "0x0", "0x00000000"}:
        return False
    return None


def qualified(name, package):
    if not name or name.startswith(("@", "?")) or "${" in name:
        return None
    if name.startswith("."):
        return package + name if package else None
    if "." not in name:
        return package + "." + name if package else None
    return name


def permission(value, source):
    return {
        "value": value or None,
        "source": source,
        "resolved": value is None or (not value.startswith(("@", "?")) and "${" not in value),
    }


def inherited(element, name, fallback, source="component"):
    value = attr(element, name)
    return permission(value, source) if value is not None else fallback


def _header_elements(root):
    from .archive_errors import ArchiveError

    if root.tag != "manifest":
        raise ArchiveError("invalid_manifest", "Root element must be manifest")
    apps = root.findall("application")
    if len(apps) > 1 or len(root.findall("uses-sdk")) > 1:
        raise ArchiveError("invalid_manifest", "Manifest has ambiguous application or SDK elements")
    return apps[0] if apps else None, root.find("uses-sdk")


def header(root):
    app, sdk = _header_elements(root)
    return {
        "package_name": root.get("package"),
        "version_name": attr(root, "versionName"),
        "version_code": attr(root, "versionCode"),
        "min_sdk": attr(sdk, "minSdkVersion"),
        "target_sdk": attr(sdk, "targetSdkVersion"),
        "application_name": attr(app, "name"),
        "resource_values_resolved": False,
    }


def summarize(root, offset, limit):
    from .archive_worker import ArchiveError, page

    app, _ = _header_elements(root)
    package = root.get("package")
    app_permission = permission(attr(app, "permission"), "application")
    if attr(app, "permission") is None:
        app_permission["source"] = "none"
    app_enabled = boolean(attr(app, "enabled"), True)
    components, activities = [], {}
    for element in app if app is not None else []:
        if element.tag not in COMPONENTS:
            continue
        kind = element.tag
        name = qualified(attr(element, "name"), package)
        effective_permission = inherited(element, "permission", app_permission)
        target = qualified(attr(element, "targetActivity"), package)
        if kind == "activity-alias" and attr(element, "permission") is None:
            # Android aliases do not inherit the target or application's permission.
            effective_permission = permission(None, "alias_default")
        enabled = boolean(attr(element, "enabled"), True)
        effective_enabled = (
            False
            if False in (enabled, app_enabled)
            else True
            if enabled is True and app_enabled is True
            else None
        )
        row = {
            "kind": kind,
            "name": name,
            "target_activity": target,
            "declarations": attributes(element),
            "exported": boolean(attr(element, "exported")),
            "exported_status": "declared"
            if boolean(attr(element, "exported")) is not None
            else "unspecified_or_unresolved",
            "enabled": boolean(attr(element, "enabled")),
            "effective_enabled": effective_enabled,
            "effective_permission": effective_permission,
            "intent_filters": [
                {
                    "declarations": attributes(intent),
                    "actions": [attributes(e) for e in intent.findall("action")],
                    "categories": [attributes(e) for e in intent.findall("category")],
                    "data": [attributes(e) for e in intent.findall("data")],
                }
                for intent in element.findall("intent-filter")
            ],
            "metadata": [attributes(e) for e in element.findall("meta-data")],
            "source": {"entry": "AndroidManifest.xml", "component_index": len(components)},
        }
        if kind == "activity-alias":
            row["target_activity_status"] = (
                "declared_before_alias" if target in activities else "unresolved_or_missing"
            )
        if kind == "provider":
            row.update(
                effective_read_permission=inherited(
                    element, "readPermission", effective_permission
                ),
                effective_write_permission=inherited(
                    element, "writePermission", effective_permission
                ),
                path_permissions=[attributes(e) for e in element.findall("path-permission")],
                grant_uri_permissions=[
                    attributes(e) for e in element.findall("grant-uri-permission")
                ],
            )
        components.append(row)
        if kind == "activity" and name:
            if name in activities:
                raise ArchiveError("invalid_manifest", "Activity name is duplicated")
            activities[name] = row
    return {
        "package_name": package,
        "declarations": attributes(root),
        "sdk": attributes(root.find("uses-sdk")),
        "application": attributes(app),
        "requested_permissions": [
            {"tag": e.tag, "declarations": attributes(e)}
            for e in root
            if e.tag in {"uses-permission", "uses-permission-sdk-23", "uses-permission-sdk-m"}
        ],
        "declared_permissions": [attributes(e) for e in root.findall("permission")],
        "application_metadata": [attributes(e) for e in app.findall("meta-data")]
        if app is not None
        else [],
        "coverage": "manifest_declarations_and_permission_inheritance",
        "resource_values_resolved": False,
        "exported_defaults_resolved": False,
        **page(components, offset, limit),
    }
