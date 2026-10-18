import numpy as np

from navigator.rank import select


def test_greedy_covers_needs():
    # unit 0 and 1 both answer need A well; unit 2 alone answers need B
    scores = np.array([[1.0, 0.0], [0.95, 0.0], [0.0, 0.8]])
    assert select(scores, np.eye(3), np.array([5, 5, 5]), 2) == [0, 2]


def test_tie_break_fewest_pages():
    scores = np.array([[1.0], [0.97], [0.5]])
    assert select(scores, np.eye(3), np.array([40, 3, 1]), 1) == [1]


def test_diversity_penalty_skips_near_duplicate():
    scores = np.array([[1.0, 0.5], [0.9, 0.5], [0.6, 0.45]])
    sims = np.array([[1, 0.99, 0.1], [0.99, 1, 0.1], [0.1, 0.1, 1]])
    assert select(scores, sims, np.array([1, 1, 1]), 2) == [0, 2]


def test_select_never_repeats():
    scores = np.array([[0.2], [0.1]])
    assert sorted(select(scores, np.eye(2), np.array([1, 1]), 5)) == [0, 1]
