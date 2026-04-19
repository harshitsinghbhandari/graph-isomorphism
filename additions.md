## 1. Spectral Embedding Penalty (strong convergence accelerator)

Compute the Laplacian eigenvectors of both graphs: $U_A$ from $L_A$, $U_B$ from $L_B$. Add:

$$\mathcal{S}(\mathbf{X}) = \|U_A - \mathbf{X} U_B\|_F^2$$

**Why it helps:** Eigenvectors encode global structure. This gives the solver a smooth, globally-informed gradient from the very start — before X is anywhere near permutation-like. It's essentially a convex surrogate for isomorphism at the spectrum level.

**Caveat:** Eigenvectors have sign/ordering ambiguity — you need to align them first (e.g. match by eigenvalue order, flip signs greedily).

---

## 2. Doubly Stochastic Entropy Regularization (keep X "spread out" early)

$$\mathcal{H}(\mathbf{X}) = -\epsilon \sum_{i,j} X_{ij} \log X_{ij}$$

Add this with a large $\epsilon$ early, then anneal $\epsilon \to 0$.

**Why it helps:** Prevents premature collapse to a bad permutation. Keeps the landscape smooth and convex-like early on. This is the core idea behind **Sinkhorn-based** relaxations and is very well studied for exactly this problem.

---

## 3. Triangle / Common Neighbor Penalty

$$\mathcal{T}(\mathbf{X}) = \|(A^2)X - X(B^2)\|_F^2$$

where $A^2 = A \cdot A$ counts paths of length 2 (i.e., common neighbors).

**Why it helps:** Your current $\mathcal{Q}$ only looks at direct edges. $A^2$ encodes 2-hop neighborhood structure, which is far more discriminative. This is cheap to compute and plugs into the same matrix-commutator form as your existing quadratic term. You can extend to $A^k$ for higher-order neighborhoods.

---

## 4. Degree Distribution Second Moment (refine the linear term)

Your current linear term uses $|d_i^A - d_j^B|$. You can enrich the cost matrix:

$$C_{ij} = \alpha|d_i^A - d_j^B| + \beta|s_i^A - s_j^B|$$

where $s_i = \sum_k A_{ik} d_k$ is the **sum of neighbor degrees** (a.k.a. the 1-hop degree profile). This is still linear in X, so it costs nothing structurally, but gives a much sharper node-compatibility signal.

---

## Suggested Combined Objective

$$Z^* = \min_X \; \underbrace{\mathcal{L}(X)}_{\text{degree}} + \underbrace{\mathcal{Q}(X)}_{\text{adjacency}} + \underbrace{\lambda_1 \mathcal{T}(X)}_{\text{2-hop}} + \underbrace{\lambda_2 \mathcal{S}(X)}_{\text{spectral}} - \underbrace{\epsilon \mathcal{H}(X)}_{\text{entropy (annealed)}}$$

with the same doubly-stochastic constraints. A good strategy: start with large $\epsilon$ and $\lambda_2$, then decay them as X sharpens — this is a **continuation method** and is standard for non-convex QPs of this type.

---

The terms $\mathcal{T}$ and enriched $\mathcal{L}$ are the easiest wins — they require no new algorithmic machinery and fit directly into your existing QP structure. The spectral term gives the biggest convergence boost but needs careful eigenvector handling.