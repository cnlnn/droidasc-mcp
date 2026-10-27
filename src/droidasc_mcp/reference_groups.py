"""Caller-grouped reference evidence for bounded, ordered input chunks.

Adapted from aimardcr/asc-mcp AscHandler.findrefs_structured (Apache-2.0),
revision 848c711f1d80a1c2577283f1fa5f475ff734aa40. See NOTICE.
Changes: retain canonical identities and all original evidence fields, and group
contiguous caller runs so flattening preserves order even across continuations.
"""

import json


def group_reference_rows(rows):
    page = ReferenceGroups()
    for row in rows:
        page.offer(row)
    return page.finish()


class ReferenceGroups:
    """Accumulate upstream-style target sets/evidence lists within a JSON byte budget."""

    def __init__(self):
        self.groups = []
        self.identity = None
        self.targets = {}
        self.size = 2
        self.sites = 0
        self.limited_by = None

    def offer(self, row, maximum=float("inf"), limit=float("inf")):
        target_field = next(
            key for key in ("callee", "field_descriptor", "value", "type_descriptor") if key in row
        )
        identity = (
            row["dex_entry"],
            row["caller"],
            target_field,
            "offset_unit" in row,
            row.get("offset_unit"),
        )
        new = identity != self.identity
        if new and len(self.groups) >= limit:
            self.limited_by = "caller_groups"
            return False
        target = row[target_field]
        target_index = 0 if new else self.targets.get(target, len(self.targets))
        evidence = {
            key: value
            for key, value in row.items()
            if key not in {"dex_entry", "caller", target_field, "offset_unit"}
        }
        evidence["target_index"] = target_index
        if new:
            group = {
                "dex_entry": identity[0],
                "caller": identity[1],
                "target_field": target_field,
                "matches": [target],
                "evidence": [evidence],
            }
            if "offset_unit" in row:
                group["offset_unit"] = row["offset_unit"]
            extra = len(json.dumps(group).encode()) + (2 if self.groups else 0)
        else:
            extra = len(json.dumps(evidence).encode()) + 2
            if target not in self.targets:
                extra += len(json.dumps(target).encode()) + 2
        if self.size + extra > maximum:
            self.limited_by = "response_bytes"
            return False
        if new:
            self.groups.append(group)
            self.identity, self.targets = identity, {target: 0}
        else:
            self.groups[-1]["evidence"].append(evidence)
            if target not in self.targets:
                self.groups[-1]["matches"].append(target)
                self.targets[target] = target_index
        self.size += extra
        self.sites += 1
        return True

    def finish(self):
        return self.groups
