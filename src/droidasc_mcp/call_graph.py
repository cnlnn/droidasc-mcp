"""Bounded breadth-first exploration of declared DEX instruction call sites."""

import json
import zlib
from collections import deque

MAX_GRAPH_BYTES = 128 * 1024


class IndexedGraph:
    def __init__(self, db):
        self.db = db

    def root(self, descriptor):
        match = self.db.execute(
            "SELECT id FROM symbols WHERE name=? AND ("
            "EXISTS(SELECT 1 FROM methods WHERE source=symbols.id) OR "
            "EXISTS(SELECT 1 FROM edges WHERE kind='method' AND target=symbols.id))",
            (descriptor,),
        ).fetchone()
        return match[0] if match else None

    def prepare(self, identities):
        pass

    def prepare_diagnostics(self, identities):
        pass

    def node(self, identity, distance):
        name, entry, without = self.db.execute(
            "SELECT s.name,d.entry,m.without_code FROM symbols s "
            "LEFT JOIN definitions d ON d.name=s.id AND d.kind='method' "
            "LEFT JOIN methods m ON m.source=s.id WHERE s.id=?",
            (identity,),
        ).fetchone()
        return {
            "method_descriptor": name,
            "depth": distance,
            "definition_resolution": "defined_in_input" if entry else "not_defined_in_input",
            "dex_entry": entry,
            "without_code": bool(without) if without is not None else None,
            "expansion_status": "not_expanded",
        }

    def adjacent(self, current, column, limit):
        from .xref_index import _unpack_edge

        rows = self.db.execute(
            "SELECT e.id,e.source,e.target,e.data,src.name,dst.name,origin.entry,d.entry "
            "FROM edges e JOIN symbols src ON src.id=e.source "
            "JOIN symbols dst ON dst.id=e.target "
            "JOIN definitions origin ON origin.name=e.source AND origin.kind='method' "
            "LEFT JOIN definitions d ON d.name=e.target AND d.kind='method' "
            f"WHERE e.kind='method' AND e.{column}=? AND e.relation='instruction' "
            "ORDER BY e.id LIMIT ?",
            (current, limit),
        )
        for edge_id, source, target, data, caller, callee, origin, entry in rows:
            row = _unpack_edge("method", data, caller, callee, "instruction", origin)
            row.update(
                target_resolution="defined_in_input" if entry else "not_defined_in_input",
                target_dex_entry=entry,
            )
            yield edge_id, target if column == "source" else source, row

    def dynamic(self, identity, limit):
        count = self.db.execute(
            "SELECT count(*) FROM dynamic WHERE source=?", (identity,)
        ).fetchone()[0]
        rows = self.db.execute(
            "SELECT data FROM dynamic WHERE source=? ORDER BY id LIMIT ?", (identity, limit)
        )
        return count, (json.loads(zlib.decompress(data)) for (data,) in rows)


def query_call_graph(db, query, *, source=None):
    source = source if source is not None else IndexedGraph(db)
    root = query["method_descriptor"]
    root_id = source.root(root)
    if root_id is None:
        return {"status": "error", "code": "method_not_found", "method_descriptor": root}
    direction = query["direction"]
    depth, max_nodes, max_edges = (query[k] for k in ("depth", "max_nodes", "max_edges"))
    nodes, edges, seen_edges, reasons = {}, [], set(), set()
    used_bytes = 4096

    def fits(*rows):
        nonlocal used_bytes
        size = sum(len(json.dumps(row).encode("utf-8")) + 2 for row in rows)
        if used_bytes + size > MAX_GRAPH_BYTES:
            reasons.add("output_bytes")
            return False
        used_bytes += size
        return True

    first = source.node(root_id, 0)
    if not fits(first):
        return {"status": "error", "code": "graph_root_exceeds_output_budget"}
    nodes[root_id] = first
    queue = deque([root_id])
    stopped = False
    while queue and not stopped:
        current = queue.popleft()
        distance = nodes[current]["depth"]
        source.prepare([current, *(key for key in queue if nodes[key]["depth"] == distance)])
        boundary = False
        columns = (
            ("source", "target")
            if direction == "both"
            else ("source" if direction == "outgoing" else "target",)
        )
        for column in columns:
            for edge_id, other, row in source.adjacent(current, column, max_edges + 1):
                if edge_id in seen_edges:
                    continue
                if distance == depth:
                    reasons.add("depth")
                    boundary = True
                    break
                if len(edges) == max_edges:
                    reasons.add("max_edges")
                    stopped = True
                    break
                new_node = None
                if other not in nodes:
                    if len(nodes) == max_nodes:
                        reasons.add("max_nodes")
                        stopped = True
                        break
                    new_node = source.node(other, distance + 1)
                if not fits(*([new_node, row] if new_node else [row])):
                    stopped = True
                    break
                if new_node:
                    nodes[other] = new_node
                    queue.append(other)
                edges.append(row)
                seen_edges.add(edge_id)
            if stopped:
                break
        nodes[current]["expansion_status"] = (
            "budget_boundary" if stopped else "depth_boundary" if boundary else "expanded"
        )

    source.prepare_diagnostics(list(nodes))
    dynamic_count, sites = 0, []
    for identity in nodes:
        limit = 20 - len(sites) if "output_bytes" not in reasons else 0
        count, rows = source.dynamic(identity, limit)
        dynamic_count += count
        if limit:
            for row in rows:
                if not fits(row):
                    break
                sites.append(row)
    return {
        "status": "ok",
        "method_descriptor": root,
        "direction": direction,
        "depth": depth,
        "max_nodes": max_nodes,
        "max_edges": max_edges,
        "max_graph_bytes": MAX_GRAPH_BYTES,
        "nodes": list(nodes.values()),
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "edge_semantics": "individual_instruction_call_sites",
        "traversal_order": "breadth_first_outgoing_then_incoming_index_order",
        "truncated": bool(reasons),
        "truncation_reasons": sorted(reasons),
        "traversal_complete_within_depth": not (reasons - {"depth"}),
        "dynamic_sites": dynamic_count,
        "unresolved_sites": sites,
        "unresolved_sites_truncated": dynamic_count > len(sites),
        "diagnostic_scope": "returned_nodes",
        "reference_semantics": "declared_method_operand",
        "limitations": ["virtual_dispatch", "reflection", "jni", "runtime_loaded_code"],
    }
