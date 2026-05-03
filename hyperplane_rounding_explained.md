# Hyperplane Rounding for Graph Isomorphism — Full Explanation

This document explains `hyperplane_rounding.py`: the theory, the algorithm, and the key concepts (SVD, random hyperplanes, Hamming distance, Goemans–Williamson).

---

## Part 1 — The Big Picture

### The Setup

You have two graphs A, B (n×n adjacency matrices) and want a permutation matrix P such that **A·P = P·B** (i.e. relabel B's vertices to match A). The exact problem is NP-hard-ish in the worst case, so a common trick is to **relax**: instead of demanding P be a 0/1 permutation, allow X to be any **doubly-stochastic** matrix (rows/cols sum to 1, entries ≥ 0). This convex set is the **Birkhoff polytope**, and its vertices are exactly the permutation matrices.

A QP elsewhere in the repo solves something like

$$\min_X \|AX - XB\|_F^2 \quad \text{s.t. } X \in \text{Birkhoff}_n$$

giving you a soft "fractional permutation" X*. Now you need to **round** X* back to an actual permutation. This file is one rounding strategy.

### Why "Hyperplane" Rounding?

The name comes from Goemans–Williamson's 1995 Max-Cut SDP. Their idea:

1. Lift each vertex to a unit vector vᵢ on the sphere (via SDP).
2. Pick a random hyperplane through the origin (= a random normal vector r).
3. Partition vertices by sign(r·vᵢ).

The probability that two vertices end up on opposite sides of the hyperplane is exactly **θ/π**, where θ is the angle between their lifted vectors. That's how you get the famous 0.878-approximation: random hyperplanes turn geometric angles into combinatorial cuts.

This file adapts the idea to the Birkhoff setting.

---

## Part 2 — The Algorithm, Step by Step

### Step 1 — Embed via SVD (`_embed_via_svd`, lines 45–59)

X* lives in matrix-land, not on a sphere. To create vector embeddings of "row-vertices" (graph A) and "column-vertices" (graph B), do an SVD:

$$X^* = U \Sigma V^T$$

Then split the singular values **symmetrically** between the two sides:

- `U_emb[i] = U[i, :r] · √σ`  ∈ ℝʳ  (vector for vertex i of A)
- `V_emb[j] = V[j, :r] · √σ`  ∈ ℝʳ  (vector for vertex j of B)

By construction, `U_emb @ V_emb.T ≈ X*[i,j] = ⟨U_emb[i], V_emb[j]⟩`. Inner products in this embedding **reconstruct X***. Vertices that X* wants to match end up close in this geometry.

`rank` truncates to top-r singular vectors — fewer dimensions = denoised but coarser.

### Step 2 — Random Hyperplane Signatures (lines 136–142)

Sample a Gaussian matrix G ∈ ℝʳˣᵏ. Each column gₜ is one random hyperplane normal. For each vertex compute a **k-bit signature**:

- `S_A = sign(U_emb @ G)` ∈ {−1, +1}ⁿˣᵏ
- `S_B = sign(V_emb @ G)` ∈ {−1, +1}ⁿˣᵏ

GW's key fact: P[sign(g·u) ≠ sign(g·v)] = θ(u,v)/π. So the **expected Hamming distance** between signatures of u and v is k·θ/π — directly proportional to the angle between embeddings. Vertices that X* paired up (small angle) get similar signatures.

The k=0 edge case (signature lies exactly on the hyperplane) is handled by mapping zeros to +1 (line 142).

### Step 3 — Hungarian Assignment on Hamming Costs (lines 145–149)

Hamming distance between bit-signatures sᵢ, sⱼ' ∈ {±1}ᵏ is:

$$d(i,j) = \frac{k - \langle s_i, s_j' \rangle}{2}$$

So `cost = (k - S_A @ S_B.T) / 2` is the n×n Hamming-distance matrix. Then `linear_sum_assignment` (the Hungarian algorithm) finds the minimum-cost perfect matching → a **permutation** P_t. This is the rounding for trial t.

### Step 4 — Many Trials, Keep the Best (lines 134–157)

Each random hyperplane bundle gives a different P. Score each one by the **integer residual** ‖A·P − P·B‖²_F (computed in int64 at lines 62–68 to avoid floating-point drift). Residual = 0 means P is an **exact isomorphism witness** — done, break early. Otherwise keep the best across `num_trials`.

The default `num_hyperplanes = ⌈4·log₂(n+2)⌉` is a heuristic motivated by: Hamming-distance error decays like O(√(log n / k)), so logarithmic k suffices.

### Why This Works (Intuition)

X* is the QP's continuous "guess." If A ≅ B and the QP recovers a near-permutation, X* has roughly one big entry per row/column. The SVD embedding exposes that as nearly-orthogonal clusters of row/column vectors that come in matching pairs. Random hyperplanes turn matched pairs into nearly-identical bit signatures, and Hamming-Hungarian recovers the matching. If A ≇ B, no single P will give residual 0, but the best-of-many-trials still gives a good local minimum.

### How It Differs from Standard Hungarian Rounding

The simpler rounding is just `linear_sum_assignment(-X*)` — match using X* directly as the cost. That's deterministic. Hyperplane rounding is **randomized**: by drawing many trials, it can sometimes find permutations that direct Hungarian misses (e.g. when X* has multiple near-tied entries the Hungarian breaks ties one way, hyperplanes explore the symmetric alternatives). The demo (lines 183–235) measures exactly this: "hyperplane-only wins" counts pairs where this method certifies isomorphism but Hungarian didn't.

### The Demo Entry Point

`__main__` either:
- Loads every saved X* from `data/matrices/*/`, runs hyperplane rounding, and tallies wins vs. the saved Hungarian result, broken down by n, **or**
- Falls back to a synthetic test: random A, random P_true, B = Pᵀ·A·P, build a noisy doubly-stochastic X* via Sinkhorn from P_true + noise, and check that rounding recovers P_true.

---

## Part 3 — Concept Deep-Dives

### 3.1 What is σ, and why truncate to rank r?

**σ (sigma)** is the vector of **singular values** of X*. The SVD decomposes any matrix as:

$$X^* = U \Sigma V^T$$

where:
- **U** is n×n with orthonormal columns (left singular vectors)
- **Σ** is a diagonal matrix with non-negative entries σ₁ ≥ σ₂ ≥ … ≥ σₙ ≥ 0 (the singular values)
- **Vᵀ** is n×n with orthonormal rows (right singular vectors)

You can rewrite this as a sum of **rank-1 pieces**:

$$X^* = \sigma_1 u_1 v_1^T + \sigma_2 u_2 v_2^T + \dots + \sigma_n u_n v_n^T$$

Each σᵢ tells you **how much "energy" lives in direction i**. Big σ = important direction; tiny σ = noise/rounding-error.

**Why truncate to rank r?**
- A doubly-stochastic X* that's close to a permutation has its mass concentrated in a few singular directions; the rest are basically numerical noise.
- Keeping all n directions embeds noise into your signatures, which corrupts the Hamming distances.
- Truncating to top r is a **denoising** step — you only embed the meaningful structure.

**Why the √σ split?** We want `⟨U_emb[i], V_emb[j]⟩ = X*[i,j]`. If we put all of σ on one side (`U_emb = U·σ`, `V_emb = V`), the inner product still works, but the two sides have **different scales** — U vectors are huge, V vectors are unit-length. Splitting symmetrically (`U_emb = U·√σ`, `V_emb = V·√σ`) keeps both sides on equal footing geometrically, which matters for hyperplane sampling (angles need both sides comparable).

### 3.2 What is G?

**G is just a bag of random directions.** Concretely:

```python
G = rng.standard_normal(size=(r, k))
```

This is an r×k matrix where **every entry is sampled i.i.d. from the standard normal N(0, 1)**.

Read column-by-column: each column **gₜ ∈ ℝʳ** is a random vector in your embedding space. That column is the **normal vector** of one random hyperplane through the origin. (A hyperplane through the origin in ℝʳ is fully determined by its normal: the hyperplane is the set of points perpendicular to that normal.)

So G is just **k random hyperplanes packed into a matrix**. Then `U_emb @ G` computes, for every vertex i and every hyperplane t, the dot product `U_emb[i] · gₜ`. Taking sign() tells you which side of hyperplane t vertex i lies on.

Why Gaussian? Because Gaussian vectors are **rotationally symmetric** — every direction in ℝʳ is equally likely. That's exactly the "random hyperplane" you want.

### 3.3 What is k?

**k is the number of hyperplanes per trial** = the **length of each vertex's signature**.

After multiplying `U_emb @ G`, every vertex gets a vector of k signs in {−1, +1}ᵏ — its "fingerprint" against the k hyperplanes.

Why does k matter? With k=1, your signature is a single bit; tons of unrelated vertices collide. With k large, signatures separate cleanly but cost more compute. The default `k = ⌈4·log₂(n+2)⌉` comes from a concentration argument: the **empirical Hamming distance** over k samples concentrates around its expectation at rate **O(1/√k)**, so logarithmic k is enough to distinguish n² vertex pairs with high probability.

### 3.4 Why is P[sign(g·u) ≠ sign(g·v)] = θ/π?

This is the geometric heart of Goemans–Williamson. Here's the proof in pictures:

**Setup:** u, v are two vectors in ℝʳ. Let θ be the angle between them. Sample g ~ N(0, Iᵣ).

**Step 1 — reduce to 2D.** The signs sign(g·u) and sign(g·v) only depend on g's projection onto the **2D plane spanned by u and v**. (Components of g perpendicular to that plane don't change either dot product's sign.) So WLOG work in 2D.

**Step 2 — Gaussian is rotationally symmetric.** In 2D, g/‖g‖ is **uniformly distributed on the unit circle** — every angle equally likely.

**Step 3 — when do the signs disagree?** Draw u and v in 2D with angle θ between them. Each vector has a perpendicular line through the origin (the hyperplane "g·u = 0" and "g·v = 0"). These two lines split the plane into **4 wedges**:

```
         g·u > 0
         g·v > 0
            |
   g·u < 0  |   g·u > 0     ← wedge of angle θ
   g·v > 0  |   g·v < 0     where signs DISAGREE
  ----------+----------
   g·u > 0  |   g·u < 0
   g·v < 0  |   g·v > 0
            |
         g·u < 0
         g·v < 0
```

The two wedges where **signs disagree** each have angular width exactly **θ** (this is just basic geometry: the two perpendicular lines meet at the same angle as u and v themselves). Together they span 2θ out of the full 2π.

**Step 4 — uniformity gives the probability.** Since g/‖g‖ is uniform on the circle:

$$P[\text{signs disagree}] = \frac{2\theta}{2\pi} = \frac{\theta}{\pi}$$

That's the magic: **a purely geometric quantity (angle) becomes a probability.** Small angle → almost always agree → similar signatures. Orthogonal (θ = π/2) → disagree half the time. Opposite (θ = π) → always disagree.

### 3.5 What is Hamming distance?

**Hamming distance between two equal-length strings = the number of positions where they differ.**

Examples:
- `1011` vs `1001` → differ at position 3 → distance **1**
- `+−+−+` vs `−+−+−` → differ everywhere → distance **5**
- `+−+−+` vs `+−+−+` → identical → distance **0**

**Connection to inner products of ±1 vectors.** If sᵢ, sⱼ ∈ {−1, +1}ᵏ, then for each coordinate t:
- if sᵢ[t] = sⱼ[t]: their product is +1
- if sᵢ[t] ≠ sⱼ[t]: their product is −1

So:

$$\langle s_i, s_j \rangle = (\text{agreements}) - (\text{disagreements}) = (k - d) - d = k - 2d$$

Solving for d:

$$d(i, j) = \frac{k - \langle s_i, s_j \rangle}{2}$$

That's exactly line 145 of the file. The matrix multiplication `S_A @ S_B.T` computes all n² inner products at once, and dividing by 2 after subtracting from k converts them to a Hamming-distance cost matrix in one shot.

**Why Hamming here?** From section 3.4, we know each bit disagrees with probability θ/π. So the **expected Hamming distance** between two signatures is:

$$\mathbb{E}[d(i,j)] = k \cdot \frac{\theta_{ij}}{\pi}$$

i.e. **Hamming distance ≈ a scaled estimate of the angle** between the two embeddings. Small Hamming = small angle = high inner product in X* = "X* wants to match these vertices." Hungarian on this matrix picks the best matching.

---

## TL;DR

1. **SVD** turns the doubly-stochastic X* into vector embeddings where inner products reconstruct X*.
2. **Random Gaussian hyperplanes** convert each vertex into a ±1 bit signature.
3. **Hamming distance** between signatures is a probabilistic estimate of the angle between embeddings — and therefore of how much X* wanted to match those two vertices.
4. **Hungarian algorithm** on the Hamming cost picks the best permutation.
5. **Many trials** with fresh random hyperplanes; keep the P with the smallest integer residual ‖AP − PB‖²_F. Residual 0 = certified isomorphism.
