"""Bounded BFS frontiers, without materializing an entire APK call index."""

import json
from collections import defaultdict

from .native_dex import DYNAMIC_NAMES, METHOD_NAMES, dex_entries
from .native_scan import class_selector, scanner, select_directory


class FrontierBudgetExceeded(Exception):
    """Use the disk-bounded full index if an unusually dense frontier will not fit."""


class FrontierGraph:
    def __init__(self, settings, bundle, query):
        self.bundle, self.query = bundle, query
        self.budget = min(settings.max_output_bytes, 8 * 1024 * 1024)
        self.cap = query["max_edges"] + 1
        self.metadata = {}
        self.visited = set()
        self.diagnostics = {}
        self.frontier = None
        self.adjacency = {}
        self.retained = 0
        self.metadata_bytes = 0
        self.passes = 0

    @staticmethod
    def record_size(value):
        return len(json.dumps(value, ensure_ascii=True).encode()) + 128

    def charge(self, value):
        self.retained += self.record_size(value)
        if self.retained > self.budget:
            raise FrontierBudgetExceeded

    @staticmethod
    def target_ids(dex, names):
        owners = set()
        for owner in {name.split("->", 1)[0] for name in names}:
            owners.update(dex.matching_types(owner))
        return {index for index in dex.owner_members(False, owners) if dex.method(index) in names}

    def root(self, descriptor):
        self.prepare([descriptor], first=True)
        if self.metadata[descriptor][0] or self.adjacency.get(("target", descriptor)):
            return descriptor
        return None

    def prepare(self, identities, *, first=False):
        if self.frontier is not None and identities[0] in self.frontier:
            return
        batch = identities[:32]
        while True:
            try:
                self._prepare(batch, first=first)
                return
            except FrontierBudgetExceeded:
                self.adjacency.clear()
                if len(batch) == 1:
                    raise
                batch = batch[: max(1, len(batch) // 2)]

    def _prepare(self, identities, *, first=False):
        names = frozenset(identities)
        self.frontier = names
        self.adjacency = defaultdict(list)
        self.metadata = {name: row for name, row in self.metadata.items() if name in self.visited}
        self.metadata_bytes = sum(self.record_size(name) for name in self.metadata)
        self.retained = self.metadata_bytes
        incoming = first or self.query["direction"] in {"incoming", "both"}
        outgoing = self.query["direction"] in {"outgoing", "both"}
        endpoints = set(names)
        # The fused cursor validates every method and instruction, not just hits.
        # Only matching callers and incoming sites cross the C/Python boundary.
        for entry, dex in dex_entries(self.bundle):
            ids = self.target_ids(dex, names)
            select = class_selector(
                dex, ids if incoming else set(), False, "all", callers=ids if outgoing else set()
            )
            directory = select_directory(dex, select)[0] if select is not None else dex.classes()
            incoming_scan = scanner(dex, ids if incoming else set(), False, True)
            outgoing_scan = scanner(dex, set(), False, False)
            for _owner, cls in directory:
                methods = cls if select is not None else dex.raw_members(cls)[1]
                for index, _flags, code in dex.ordered_methods(methods):
                    if not code:
                        continue
                    caller = dex.method(index)
                    # Incoming callers need only frontier operands. Both scanners
                    # still validate every instruction, including nonmatching ones.
                    scan = outgoing_scan if outgoing and caller in names else incoming_scan
                    for position, address, op, _count in scan(code):
                        if op not in METHOD_NAMES:
                            continue
                        callee_id = dex.u16(position + 2)
                        columns = []
                        if outgoing and caller in names:
                            columns.append(("source", caller))
                        if incoming and callee_id in ids:
                            columns.append(("target", dex.method(callee_id)))
                        columns = [key for key in columns if len(self.adjacency[key]) < self.cap]
                        if not columns:
                            continue
                        callee = dex.method(callee_id)
                        row = {
                            "caller": caller,
                            "callee": callee,
                            "dex_entry": entry,
                            "instruction_offset": address,
                            "offset_unit": "code_units_from_method_start",
                            "opcode": METHOD_NAMES[op],
                        }
                        if op in {0xFA, 0xFB}:
                            row["call_site_prototype"] = dex.proto(dex.u16(position + 6))
                        self.charge(row)
                        identity = (entry, caller, address)
                        for key in columns:
                            self.adjacency[key].append((identity, row))
                        endpoints.update((caller, callee))
        self.passes += 1
        self.resolve(endpoints - self.metadata.keys())

    def resolve(self, names, *, diagnostics=False):
        if not names:
            return
        owners = {name.split("->", 1)[0] for name in names}
        for name in names:
            if name not in self.metadata:
                previous = self.retained
                self.charge(name)
                self.metadata_bytes += self.retained - previous
                self.metadata[name] = (None, None)
            if diagnostics:
                self.diagnostics[name] = (0, [])
        for entry, dex in dex_entries(self.bundle):
            for owner, cls in dex.classes(ordered=False):
                if owner not in owners:
                    continue
                for index, _flags, code in dex.raw_members(cls)[1]:
                    name = dex.method(index)
                    if name not in names:
                        continue
                    self.metadata[name] = (entry, not bool(code))
                    if not diagnostics or not code:
                        continue
                    count, sites = 0, []
                    for _position, address, op, _ in scanner(dex, set(), False, False)(code):
                        if not 0xFA <= op <= 0xFE:
                            continue
                        count += 1
                        if len(sites) < 20:
                            row = {
                                "caller": name,
                                "dex_entry": entry,
                                "instruction_offset": address,
                                "opcode": DYNAMIC_NAMES[op],
                                "reason": "dynamic_target_not_resolved",
                            }
                            self.charge(row)
                            sites.append(row)
                    self.diagnostics[name] = (count, sites)

    def node(self, identity, distance):
        self.visited.add(identity)
        entry, without = self.metadata[identity]
        return {
            "method_descriptor": identity,
            "depth": distance,
            "definition_resolution": "defined_in_input" if entry else "not_defined_in_input",
            "dex_entry": entry,
            "without_code": without,
            "expansion_status": "not_expanded",
        }

    def adjacent(self, current, column, limit):
        for identity, row in self.adjacency.get((column, current), ())[:limit]:
            other = row["callee" if column == "source" else "caller"]
            entry = self.metadata[row["callee"]][0]
            yield (
                identity,
                other,
                {
                    **row,
                    "target_resolution": "defined_in_input" if entry else "not_defined_in_input",
                    "target_dex_entry": entry,
                },
            )

    def prepare_diagnostics(self, identities):
        self.resolve(set(identities), diagnostics=True)

    def dynamic(self, identity, limit):
        count, rows = self.diagnostics[identity]
        return count, rows[:limit]


def query_frontier(settings, bundle, query):
    from .call_graph import query_call_graph

    source = FrontierGraph(settings, bundle, query)
    return {
        "backend": "native-dex-frontier",
        "backend_version": "1",
        "instruction_scan_complete": True,
        "scan_errors": 0,
        "runtime_target_resolution": "not_performed",
        **query_call_graph(None, query, source=source),
    }
