# Person reading and notes
Gram-Schmidt process is a mathematical algorithm used to take a set of vectors and transform them into an orthogonal or orthonormal set. It is a way of finding a set of two or more vectors that are perpendicular to each other.

---

## FW derivations for Ch. 3 (SME → DM mapping) — reading & re-derivation plan
*Added 2026-08-01. Point of this section: don't lose track of what I've actually verified by hand vs. what I still owe myself. Also doubles as the paper trail for my supervisor — where each result comes from, and what's still TODO on my end.*

### Status check, all three coefficients
- **b_μ**: done, hand-checkable via `FW_bmu_term.ipynb`. Watch the sign convention: `FW_derivation_bmy.md` uses $\mathcal L_b=-b_\mu\bar\psi\gamma_5\gamma^\mu\psi$ (γ5 first); the notebook itself uses the opposite ordering and gets the opposite sign for $H_{NR}(b_i)$. Cite the theory note's sign in the thesis, not the notebook's raw printout — they're the same physics, just opposite convention.
- **H_μν**: done, verified via `FW_Hmunu_term.ipynb`.
- **d_μν**: this is the one I actually need to sit down and re-derive myself, pen and paper. Notes below.

### d_μν — where I went wrong, and exactly where to read it properly

**What happened:** I originally wrote $\mathcal L_d = d_{\mu\nu}\bar\psi\gamma_5\sigma^{\mu\nu}\psi$ — basically copied $H_{\mu\nu}$'s structure and stuck a $\gamma_5$ on it. Seemed reasonable by analogy. It's wrong. Running it through the same numeric check that caught my $b_\mu$ sign bug earlier, it didn't reproduce the mass-enhancement claim I'd written down by hand.

**Primary source — go read this myself, don't take the summary below on faith:**
> V.A. Kostelecký & C.D. Lane, *"Constraints on Lorentz Violation from Clock-Comparison Experiments,"* Phys. Rev. D **60**, 116010 (1999). arXiv:hep-ph/9908504.
> — Section **II.A, "Lagrangian and Hamiltonian"**, Eqs. **(1)–(4)**. (Roughly pages 3–4 of the arXiv PDF.)

Note to self on citations: I had `Kostelecký & Lane (1999), "Nonrelativistic quantum Hamiltonian for Lorentz violation," J. Math. Phys. 40, 6245` in my bibliography. That's a DIFFERENT paper by the same two authors, same year — not the one with Eqs. (1)-(4) above. Need to double check which one I actually mean each place I cite "Kostelecký & Lane 1999" in the thesis and fix accordingly.

**The structure, from Eq. (1)-(3) — copy this out by hand from the actual PDF, not from here:**
$$\mathcal L = \tfrac12 i\bar\psi\Gamma^\nu\overleftrightarrow\partial_\nu\psi - \bar\psi M\psi$$
- $M$ = **mass sector**: $m + a_\mu\gamma^\mu + b_\mu\gamma_5\gamma^\mu + \tfrac12 H_{\mu\nu}\sigma^{\mu\nu}$. $H_{\mu\nu}$ lives here — that's the part I wrongly borrowed for $d_{\mu\nu}$.
- $\Gamma^\nu$ = **kinetic sector**: $\gamma^\nu + c^{\mu\nu}\gamma_\mu + d^{\mu\nu}\gamma_5\gamma_\mu + \ldots$. $d_{\mu\nu}$ actually lives HERE, next to $c_{\mu\nu}$, not next to $H_{\mu\nu}$.

Paper states directly (worth re-finding and quoting exactly when I write this into the thesis properly): params in $M$ carry mass dimension, params in $\Gamma$ are dimensionless; $c_{\mu\nu}$ and $d_{\mu\nu}$ are **traceless**, $H_{\mu\nu}$ is the antisymmetric one. So my "$d_{00}=0$ by antisymmetry" line was importing $H_{\mu\nu}$'s property onto the wrong tensor — need to fix that reasoning chain in my own words, not just the conclusion.

**What's actually left for me to derive by hand:**
1. Take $\mathcal L_d = \tfrac12 i\bar\psi\,d^{\mu\nu}\gamma_5\gamma_\mu\overleftrightarrow\partial_\nu\psi$, do the Euler–Lagrange variation w.r.t. $\bar\psi$ myself (same method as any Dirac Lagrangian — treat $\bar\psi$ and $\partial_\nu\bar\psi$ as independent). Confirm I land on $(i\gamma^\mu\partial_\mu + i\,d^{\mu\nu}\gamma_5\gamma_\mu\partial_\nu - m)\psi=0$.
2. Go to momentum space ($i\partial_\mu\to p_\mu$, watch the metric — mine is $(+,-,-,-)$), multiply through by $\gamma^0$, isolate $H_d = -d^{\mu\nu}p_\nu\Gamma_\mu$ with $\Gamma_\mu \equiv \gamma^0\gamma_5\gamma_\mu$ (lower-index $\mu$).
3. Multiply out $\Gamma_0$ and $\Gamma_i$ by hand in the Dirac representation — don't just trust sympy's answer. I should get $\Gamma_0=-\gamma_5$ (odd) and $\Gamma_i=+\Sigma^i$ (even) — verify this myself with actual $4\times4$ matrix multiplication.
4. Even piece ($\mu=i$): no FW iteration needed, same situation as $b_i$. Get $H_{NR}(d_{i0})$ and $H_{NR}(d_{ij})$ this way, at leading order ($E\to m$).
5. Odd piece ($\mu=0$): needs the FW $\mathcal O^2/2m$ cross-term with $\boldsymbol\alpha\cdot\mathbf p$ — same machinery as $b_0$ (worked through once already in `FW_derivation_bmy.md` §3.2b, re-derive it there too if I've forgotten the steps). Get $H_{NR}(d_{00})$ this way.
6. Convert my upper-index $d^{\mu\nu}$ (as it appears in $\Gamma^\nu$) to Kostelecký & Lane's lower-index convention in their Eq. (4), and check my numbers against theirs directly. This is where the $(+,-,-,-)$ metric raising/lowering needs care — I keep tripping on this, slow down here.

**Open question I have NOT resolved, need to actually think about it rather than paper over it:** my derivation matches K&L's Eq. (4) exactly for the $d_{i0}\to m\sigma^i$ piece (good sign the method is right), but the momentum-dependent pieces ($d_{ij}$, $d_{00}$) come out with the opposite overall sign from their Eq. (4), even though the operator structure is right. Current best guess: K&L's actual derivation of Eq. (4) includes a wavefunction-renormalization step for kinetic-sector coefficients that my plain "insert $i\partial_\nu\to p_\nu$ into the equation of motion" approach skips. Need to find where in the SME literature that renormalization step is spelled out (check Kostelecký & Mewes 2001, and check whether K&L have an appendix on this) and redo that part properly by hand. Do NOT just flip the sign to make it match — figure out why it's there.

**Where to cross-check — only after I've attempted 1-6 myself, not before:**
- `docs/theory_notes/FW_derivation_dmunu.md` — corrected theory note.
- `derivations/sympy/FW_dmunu_term.ipynb` — executed symbolic notebook, same Dirac-algebra tooling used for $b_\mu$/$H_{\mu\nu}$.
- Both were produced with AI assistance (Claude) — it located the Kostelecký & Lane reference and ran the numeric Dirac-algebra check that caught my original error. It did **not** do the by-hand derivation/proof in steps 1-6 above for me; that's still mine to actually do, and is the part that matters for demonstrating I understand it.