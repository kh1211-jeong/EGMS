# topology_provider.py
from equipment_provider import list_equipments


def get_topology():
    items = list_equipments()

    # ----- Node 구성 -----
    nodes = []
    eqp_map = {}
    for it in items:
        node = {
            "id": it["eqp_no"],
            "label": it["eqp_name"],
            "category": it["type"],
            "building": it["building"],
            "location": it["location"],
        }
        nodes.append(node)
        eqp_map[it["eqp_no"]] = it

    # ----- Edge 구성 (parent → child) -----
    edges = []
    for it in items:
        parent = it.get("parent_eqp_no")
        if parent and parent in eqp_map:
            edges.append({
                "source": parent,
                "target": it["eqp_no"]
            })

    # ----- topology 트리 구성 -----
    # children 맵 생성
    children = {it["eqp_no"]: [] for it in items}
    roots = []

    for it in items:
        eqp_no = it["eqp_no"]
        parent = it.get("parent_eqp_no")

        if parent and parent in children:
            children[parent].append(eqp_no)
        else:
            roots.append(eqp_no)

    # 재귀 트리 생성
    def build_tree(eqp_no):
        base = eqp_map[eqp_no]
        return {
            "id": eqp_no,
            "name": base["eqp_name"],
            "type": base["type"],
            "children": [build_tree(ch) for ch in children[eqp_no]]
        }

    topology = [build_tree(r) for r in roots]

    # ----- 최종 반환 -----
    return {
        "nodes": nodes,
        "edges": edges,
        "topology": topology,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
