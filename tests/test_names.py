import pytest
from atmo import names


@pytest.mark.parametrize('separator', ['-', '_'])
def test_names(separator):
    name = names.random_scientist(separator=separator)
    adjective, noun, suffix = name.split(separator)
    assert adjective in names.adjectives
    assert noun in names.scientists
    assert len(suffix) == 4
    assert int(suffix)
