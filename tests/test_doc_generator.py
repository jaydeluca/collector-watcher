"""Tests for documentation generator."""

from pathlib import Path

import pytest

from collector_watcher.doc_generator import DocGenerator


@pytest.fixture
def doc_generator():
    """Create a DocGenerator instance for testing."""
    return DocGenerator(version="v0.138.0")


class TestGetStabilityBySignal:
    """Tests for get_stability_by_signal function."""

    def test_get_stability_single_signal_beta(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["metrics"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"metrics": "beta"}

    def test_get_stability_multiple_signals_same_level(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["traces", "metrics", "logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "beta", "metrics": "beta", "logs": "beta"}

    def test_get_stability_multiple_signals_different_levels(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["traces", "metrics"], "alpha": ["logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "beta", "metrics": "beta", "logs": "alpha"}

    def test_get_stability_extension(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["extension"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"extension": "beta"}

    def test_get_stability_no_metadata(self, doc_generator):
        assert doc_generator.get_stability_by_signal({}) == {}
        assert doc_generator.get_stability_by_signal(None) == {}

    def test_get_stability_no_stability_field(self, doc_generator):
        metadata = {"status": {}}
        assert doc_generator.get_stability_by_signal(metadata) == {}

    def test_get_stability_empty_stability(self, doc_generator):
        metadata = {"status": {"stability": {}}}
        assert doc_generator.get_stability_by_signal(metadata) == {}

    def test_get_stability_partial_signals(self, doc_generator):
        metadata = {"status": {"stability": {"alpha": ["traces"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "alpha"}

    def test_get_stability_development_level(self, doc_generator):
        metadata = {"status": {"stability": {"development": ["traces", "logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "development", "logs": "development"}

    def test_get_stability_unmaintained_level(self, doc_generator):
        metadata = {"status": {"stability": {"unmaintained": ["extension"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"extension": "unmaintained"}
