"""
AHU (Aho-Hopcroft-Ullman 1974) Tree Isomorphism Algorithm
No recursion, no NetworkX isomorphism functions.
"""
from collections import deque


def find_centroid(T):
    """
    Find centroid(s) of tree T via iterative leaf-removal.
    Returns a list of 1 or 2 centroid nodes.
    """
    n = len(T)
    if n == 1:
        return list(T.nodes())

    degree = {node: T.degree(node) for node in T.nodes()}
    queue = deque(node for node in T.nodes() if degree[node] == 1)
    remaining = n

    while remaining > 2:
        next_leaves = []
        for _ in range(len(queue)):
            leaf = queue.popleft()
            remaining -= 1
            for neighbor in T.neighbors(leaf):
                if degree[neighbor] > 1:
                    degree[neighbor] -= 1
                    if degree[neighbor] == 1:
                        next_leaves.append(neighbor)
        queue.extend(next_leaves)

    return list(queue)


def root_tree(T, root):
    """
    Root tree T at `root` via iterative BFS.
    Returns (children dict, bfs_order list, level dict).
    """
    children = {node: [] for node in T.nodes()}
    level = {root: 0}
    bfs_order = [root]
    queue = deque([root])
    visited = {root}

    while queue:
        node = queue.popleft()
        for neighbor in T.neighbors(node):
            if neighbor not in visited:
                visited.add(neighbor)
                children[node].append(neighbor)
                level[neighbor] = level[node] + 1
                bfs_order.append(neighbor)
                queue.append(neighbor)

    return children, bfs_order, level


def ahu_label(children, bfs_order, level, shared_mapping):
    """
    Assign AHU labels bottom-up using a shared level->tuple->int mapping.
    Processes nodes in reverse BFS order (leaves first, root last).
    Returns label dict.
    """
    label = {}

    for node in reversed(bfs_order):
        lv = level[node]
        child_labels = tuple(sorted(label[c] for c in children[node]))

        if lv not in shared_mapping:
            shared_mapping[lv] = {}
        mapping = shared_mapping[lv]

        if child_labels not in mapping:
            mapping[child_labels] = len(mapping)
        label[node] = mapping[child_labels]

    return label


def _compare(root1, children1, bfs1, level1,
             root2, children2, bfs2, level2):
    """
    Label both trees simultaneously with a shared level->tuple->int mapping.
    Returns True if root labels match.
    """
    shared_mapping = {}

    # Determine max depth across both trees
    max_depth = 0
    if level1:
        max_depth = max(max_depth, max(level1.values()))
    if level2:
        max_depth = max(max_depth, max(level2.values()))

    # Group nodes by level for both trees
    by_level1 = {}
    for node in bfs1:
        lv = level1[node]
        by_level1.setdefault(lv, []).append(node)

    by_level2 = {}
    for node in bfs2:
        lv = level2[node]
        by_level2.setdefault(lv, []).append(node)

    label1 = {}
    label2 = {}

    # Process from deepest level up to 0
    for lv in range(max_depth, -1, -1):
        level_map = {}  # tuple -> int, shared for this level

        # Collect signatures from tree1 at this level
        for node in by_level1.get(lv, []):
            sig = tuple(sorted(label1[c] for c in children1[node]))
            if sig not in level_map:
                level_map[sig] = len(level_map)
            label1[node] = level_map[sig]

        # Collect signatures from tree2 at this level (same mapping)
        for node in by_level2.get(lv, []):
            sig = tuple(sorted(label2[c] for c in children2[node]))
            if sig not in level_map:
                level_map[sig] = len(level_map)
            label2[node] = level_map[sig]

        shared_mapping[lv] = level_map

    return label1[root1] == label2[root2]


def are_isomorphic(T1, T2):
    """
    Test if two unrooted trees T1 and T2 are isomorphic using AHU algorithm.
    """
    if len(T1) != len(T2):
        return False

    if len(T1) == 1:
        return True

    centroids1 = find_centroid(T1)
    centroids2 = find_centroid(T2)

    # If centroid counts differ, not isomorphic
    if len(centroids1) != len(centroids2):
        return False

    def check_pair(c1, c2):
        children1, bfs1, level1 = root_tree(T1, c1)
        children2, bfs2, level2 = root_tree(T2, c2)
        return _compare(c1, children1, bfs1, level1,
                        c2, children2, bfs2, level2)

    if len(centroids1) == 1:
        return check_pair(centroids1[0], centroids2[0])
    else:
        # Try both pairings
        if check_pair(centroids1[0], centroids2[0]):
            return True
        return check_pair(centroids1[0], centroids2[1])
