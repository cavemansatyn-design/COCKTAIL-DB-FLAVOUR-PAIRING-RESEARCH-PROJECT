"""09 Co-occurrence. Figures 20-21."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import INGREDIENTS_LONG, TABLES, save_json, save_table  # noqa: E402
from plot_style import COLORS, apply_style, savefig  # noqa: E402

apply_style()

TOP_N = 40
MIN_COOC = 25


def main():
    long_df = pd.read_csv(INGREDIENTS_LONG)
    freq = pd.read_csv(TABLES / "ingredient_frequency_standard.csv")
    top = freq.head(TOP_N)["ingredient"].tolist()
    recs = (
        long_df[long_df["standard"].isin(top)]
        .groupby("row_id")["standard"]
        .apply(lambda s: sorted(set(s)))
    )
    n_rec = long_df["row_id"].nunique()
    idx = {ing: i for i, ing in enumerate(top)}
    C = np.zeros((TOP_N, TOP_N), dtype=int)
    for ings in recs:
        for a in range(len(ings)):
            for b in range(a + 1, len(ings)):
                i, j = idx[ings[a]], idx[ings[b]]
                C[i, j] += 1
                C[j, i] += 1
    fi = freq.set_index("ingredient").loc[top, "frequency"].to_numpy()
    pmi = np.full_like(C, np.nan, dtype=float)
    for i in range(TOP_N):
        for j in range(TOP_N):
            if i == j:
                continue
            if C[i, j] == 0:
                pmi[i, j] = np.nan
                continue
            pij = C[i, j] / n_rec
            pi = fi[i] / n_rec
            pj = fi[j] / n_rec
            pmi[i, j] = np.log(pij / (pi * pj))

    fig, ax = plt.subplots(figsize=(9.4, 8.4))
    im = ax.imshow(C, cmap="Blues")
    ax.set_xticks(range(TOP_N))
    ax.set_yticks(range(TOP_N))
    ax.set_xticklabels(top, rotation=90, fontsize=6.5)
    ax.set_yticklabels(top, fontsize=6.5)
    fig.colorbar(im, ax=ax, fraction=0.046, label="Co-occurring recipes")
    ax.set_title(f"Co-occurrence counts among top {TOP_N} ingredients")
    ax.grid(False)
    savefig(fig, "fig20_cooccurrence_heatmap")

    G = nx.Graph()
    for ing, f in zip(top, fi):
        G.add_node(ing, freq=int(f))
    edges = []
    for i in range(TOP_N):
        for j in range(i + 1, TOP_N):
            if C[i, j] >= MIN_COOC and np.isfinite(pmi[i, j]) and pmi[i, j] > 0.4:
                G.add_edge(top[i], top[j], weight=float(pmi[i, j]), cooc=int(C[i, j]))
                edges.append({"a": top[i], "b": top[j], "cooc": int(C[i, j]), "pmi": float(pmi[i, j])})
    save_table(pd.DataFrame(edges).sort_values("pmi", ascending=False) if edges else pd.DataFrame(columns=["a", "b", "cooc", "pmi"]), "ingredient_pmi_edges.csv")

    fig, ax = plt.subplots(figsize=(9.6, 8.2))
    pos = nx.spring_layout(G, seed=2, k=1.3 / np.sqrt(max(len(G), 1)))
    weights = [G[u][v]["weight"] for u, v in G.edges()]
    sizes = [80 + 900 * (G.nodes[n]["freq"] / fi.max()) for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=sizes, node_color=COLORS["light"], edgecolors=COLORS["blue"])
    if weights:
        nx.draw_networkx_edges(G, pos, ax=ax, width=[0.4 + 1.6 * (w / max(weights)) for w in weights], edge_color=COLORS["muted"], alpha=0.8)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_family="DejaVu Serif")
    ax.set_title(f"Positive-PMI co-occurrence network (top {TOP_N}; min co-occurrence {MIN_COOC})")
    ax.axis("off")
    ax.grid(False)
    savefig(fig, "fig21_association_network")

    top_edges = sorted(edges, key=lambda e: -e["pmi"])[:15]
    payload = {
        "top_n": TOP_N,
        "n_recipes": int(n_rec),
        "min_cooccurrence": MIN_COOC,
        "n_edges": len(edges),
        "top_pmi_edges": top_edges,
        "caveat": "Co-occurrence and PMI measure joint recipe incidence, not flavor chemistry or causality.",
    }
    save_json("09_cooccurrence.json", payload)
    print("cooccurrence complete", len(edges))


if __name__ == "__main__":
    main()
