import pytest

from src.scoring import band, score


def test_score_is_likelihood_times_impact():
    assert score(4, 5) == 20


@pytest.mark.parametrize("s,expected", [(1, "Low"), (5, "Low"), (6, "Medium"), (11, "Medium"),
                                        (12, "High"), (19, "High"), (20, "Critical"), (25, "Critical")])
def test_band_thresholds(s, expected):
    assert band(s) == expected


@pytest.mark.parametrize("l,i", [(0, 3), (3, 6), (-1, 2)])
def test_score_rejects_out_of_range(l, i):
    with pytest.raises(ValueError):
        score(l, i)
