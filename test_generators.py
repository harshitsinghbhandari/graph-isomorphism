import unittest

import networkx as nx
import numpy as np

from generators import make_isomorphic_pair


class MakeIsomorphicPairTests(unittest.TestCase):
    def test_isomorphic_pairs_are_not_matrix_identical_in_solver_basis(self):
        rng = np.random.default_rng(42)

        found_non_identical = False
        for _ in range(100):
            g1, g2 = make_isomorphic_pair(8, rng)
            a = nx.to_numpy_array(g1, nodelist=sorted(g1.nodes()))
            b = nx.to_numpy_array(g2, nodelist=sorted(g2.nodes()))
            if not np.array_equal(a, b):
                found_non_identical = True
                break

        self.assertTrue(found_non_identical)


if __name__ == "__main__":
    unittest.main()
