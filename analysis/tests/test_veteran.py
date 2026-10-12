"""The Veteran's choice study (analysis/veteran_choice.py): the choice likelihood and its gradients, that
the fits recover what was planted, that an untrained net is Quality, and (with the local replay data)
that every generated neighbour is a legal build."""

from __future__ import annotations

import unittest

import numpy as np

import support  # noqa: F401  (puts analysis/ on the path)
import veteran_choice as vc


def synthetic(n_builds: int = 400, n_cards: int = 60, n_cells: int = 4, seed: int = 0, theta=None, s: float = 0.05):
    """Builds whose neighbours are chosen against under known cell multipliers `theta`."""
    rng = np.random.default_rng(seed)
    value = rng.uniform(50, 400, n_cards)
    cell = rng.integers(0, n_cells, n_cards)
    theta = np.zeros(n_cells) if theta is None else np.asarray(theta, float)
    true_v = value * np.exp(theta[cell])
    rows_b, rows_o, rows_i = [], [], []
    for b in range(n_builds):
        # Candidate one-card changes; the observed build is the best of a random set under the true values
        # plus Gumbel noise, so the comparisons it wins are exactly what a conditional logit generates.
        cands = [(rng.integers(n_cards), rng.integers(n_cards)) for _ in range(12)]
        u = np.array([true_v[i] - true_v[o] for o, i in cands]) * s + rng.gumbel(size=12)
        u0 = rng.gumbel()
        best = int(np.argmax(np.append(u, u0)))
        if best == 12:                                       # the observed build is the unchanged one
            nb = cands
        else:                                                # re-centre on the chosen change
            o_b, i_b = cands[best]
            nb = [(i_b, o_b)] + [c for k, c in enumerate(cands) if k != best]
        for o, i in nb:
            rows_b.append(b)
            rows_o.append(o)
            rows_i.append(i)
    prob = vc.Problem(np.array(rows_b), np.array(rows_o), np.array(rows_i), np.zeros(len(rows_b)),
                      np.ones(n_builds), n_builds, n_cards)
    cards = vc.Cards([("f", str(k)) for k in range(n_cards)], {}, value, cell, [f"c{k}" for k in range(n_cells)],
                     np.zeros(n_cards, bool), np.arange(n_cards), np.zeros(n_cards), value * 1.0)
    return prob, cards


class LikelihoodTests(unittest.TestCase):
    def test_gradients_match_finite_differences(self) -> None:
        prob, cards = synthetic(n_builds=80)
        prob.cmd = np.random.default_rng(1).normal(0, 20, prob.b.size)
        V = cards.value * 1.1
        ls, lk = np.log(0.03), np.log(0.7)
        _, gV, gs, gk = vc.nll(V, ls, prob, log_k=lk)
        f = lambda V_, ls_, lk_: vc.nll(V_, ls_, prob, grad=False, log_k=lk_)[0]
        for c in (0, 7, 33):
            e = np.zeros_like(V)
            e[c] = 1e-3
            self.assertAlmostEqual(gV[c], (f(V + e, ls, lk) - f(V - e, ls, lk)) / 2e-3, places=5)
        self.assertAlmostEqual(gs, (f(V, ls + 1e-6, lk) - f(V, ls - 1e-6, lk)) / 2e-6, places=3)
        self.assertAlmostEqual(gk, (f(V, ls, lk + 1e-6) - f(V, ls, lk - 1e-6)) / 2e-6, places=3)

    def test_net_gradient_and_untrained_net_is_quality(self) -> None:
        rng = np.random.default_rng(2)
        X = rng.normal(size=(50, 7))
        p = vc.Net.init(7, 3)
        self.assertEqual(float(np.abs(vc.Net.forward(p, X)[0]).max()), 0.0)    # output starts at 0
        p = p + rng.normal(0, 0.05, p.size)
        gg = rng.normal(size=50)
        g, cache = vc.Net.forward(p, X)
        grad = vc.Net.backward(p, X, cache, gg)
        for j in rng.choice(p.size, 6, replace=False):
            e = np.zeros_like(p)
            e[j] = 1e-6
            num = ((vc.Net.forward(p + e, X)[0] - vc.Net.forward(p - e, X)[0]) @ gg) / 2e-6
            self.assertAlmostEqual(grad[j], num, places=5)

    def test_linear_fit_recovers_planted_multipliers(self) -> None:
        planted = np.array([0.4, 0.0, -0.3, 0.1])
        prob, cards = synthetic(n_builds=3000, theta=planted, seed=4)
        fit = vc.fit_linear(prob, cards, tau=5.0)
        got = fit["theta"] - fit["theta"].mean()
        np.testing.assert_allclose(got, planted - planted.mean(), atol=0.12)

    def test_no_signal_leaves_quality(self) -> None:
        prob, cards = synthetic(n_builds=1500, seed=5)
        fit = vc.fit_linear(prob, cards, tau=0.25)
        self.assertLess(float(np.abs(fit["theta"]).max()), 0.15)


@unittest.skipUnless((vc.LOCAL / "players.txt").exists() and vc.ckpt.veteran("neighbours").exists(),
                     "needs the local replay data (analysis/local/veteran/) and the cached neighbourhoods")
class NeighbourTests(unittest.TestCase):
    def test_every_neighbour_is_a_legal_build(self) -> None:
        # Re-check a sample of generated neighbours with the full rules: cost after rebates ≤ 10 000 and the
        # rules engine's limits; and that commander variants never move.
        builds = vc.elite_builds()
        nbs = vc.all_neighbours(builds, 1, 0.0)
        vc._init_worker()
        catalog = vc._W["catalog"]
        rng = np.random.default_rng(0)
        checked = 0
        for k in rng.choice(len(builds), 25, replace=False):
            b, nb = builds[k], nbs[k]
            roster = catalog.cards_for_faction(b.faction)
            commander = catalog.resolve_selection(b.faction, [b.commander])
            for o, i in [nb[j] for j in rng.choice(len(nb), min(20, len(nb)), replace=False)] if nb else []:
                keys = list(b.units)
                if o is not None:
                    keys.remove(o)
                if i is not None:
                    keys.append(i)
                sel = catalog.resolve_selection(b.faction, keys) + commander
                with self.subTest(build=k, out=o, inn=i):
                    self.assertLessEqual(vc.abr.calculate_army_cost(sel, roster, b.faction).final_cost, vc.FUNDS)
                    self.assertTrue(vc.abr.check_known_limits(sel, b.faction, staff_slot_index=len(sel) - 1,
                                                              recruitable_cards=roster).valid)
                checked += 1
        self.assertGreater(checked, 200)


if __name__ == "__main__":
    unittest.main()
