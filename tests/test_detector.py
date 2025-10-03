"""Tests for change detector."""

import pytest

from collector_watcher.detector import Change, ChangeDetector, ChangeType


def make_inventory(components_dict):
    """Helper to create inventory with all component types."""
    full_components = {
        "connector": [],
        "exporter": [],
        "extension": [],
        "processor": [],
        "receiver": [],
    }
    full_components.update(components_dict)
    return {"repository": "test", "components": full_components}


@pytest.fixture
def empty_inventory():
    """Empty inventory structure."""
    return {
        "repository": "test",
        "components": {
            "connector": [],
            "exporter": [],
            "extension": [],
            "processor": [],
            "receiver": [],
        },
    }


@pytest.fixture
def basic_inventory():
    """Basic inventory with a few components."""
    return {
        "repository": "test",
        "components": {
            "connector": [],
            "exporter": [],
            "extension": [],
            "processor": [
                {"name": "batchprocessor", "has_metadata": True, "metadata": {"type": "batch"}}
            ],
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "status": {
                            "class": "receiver",
                            "stability": {"stable": ["metrics", "traces"]},
                        },
                    },
                }
            ],
        },
    }


def test_no_changes(basic_inventory):
    """Test when inventories are identical."""
    detector = ChangeDetector(basic_inventory, basic_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 0
    assert not detector.has_changes()


def test_component_added(empty_inventory, basic_inventory):
    """Test detecting new component."""
    detector = ChangeDetector(empty_inventory, basic_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 2
    assert detector.has_changes()

    # Check for otlpreceiver addition
    otlp_change = next(c for c in changes if c.component_name == "otlpreceiver")
    assert otlp_change.change_type == ChangeType.COMPONENT_ADDED
    assert otlp_change.component_type == "receiver"
    assert "otlpreceiver" in otlp_change.description


def test_component_removed(empty_inventory, basic_inventory):
    """Test detecting removed component."""
    detector = ChangeDetector(basic_inventory, empty_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 2
    assert detector.has_changes()

    # Check for removal
    removal_change = next(c for c in changes if c.component_name == "otlpreceiver")
    assert removal_change.change_type == ChangeType.COMPONENT_REMOVED
    assert removal_change.old_value is not None


def test_metadata_added():
    """Test detecting metadata added to existing component."""
    old_inventory = make_inventory(
        {
            "receiver": [{"name": "customreceiver", "has_metadata": False}],
        }
    )

    new_inventory = make_inventory(
        {
            "receiver": [
                {
                    "name": "customreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "custom"},
                }
            ],
        }
    )

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.METADATA_ADDED
    assert changes[0].component_name == "customreceiver"


def test_metadata_removed():
    """Test detecting metadata removed from component."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "customreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "custom"},
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [{"name": "customreceiver", "has_metadata": False}],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.METADATA_REMOVED


def test_stability_changed():
    """Test detecting stability level changes."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "status": {"stability": {"beta": ["metrics"]}},
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "status": {"stability": {"stable": ["metrics"]}},
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.STABILITY_CHANGED
    assert changes[0].old_value == {"beta": ["metrics"]}
    assert changes[0].new_value == {"stable": ["metrics"]}


def test_attribute_added():
    """Test detecting new attribute."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "otlp", "attributes": {}},
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "attributes": {"direction": {"description": "Direction", "type": "string"}},
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.ATTRIBUTE_ADDED
    assert changes[0].details["attribute_name"] == "direction"


def test_attribute_removed():
    """Test detecting removed attribute."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "attributes": {"direction": {"description": "Direction", "type": "string"}},
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "otlp", "attributes": {}},
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.ATTRIBUTE_REMOVED


def test_attribute_modified():
    """Test detecting modified attribute."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "attributes": {"direction": {"description": "Direction", "type": "string"}},
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "attributes": {
                            "direction": {
                                "description": "Data flow direction",
                                "type": "string",
                            }
                        },
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.ATTRIBUTE_MODIFIED


def test_metric_added():
    """Test detecting new metric."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "otlp", "metrics": {}},
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "metrics": {
                            "system.cpu.usage": {
                                "description": "CPU usage",
                                "unit": "%",
                            }
                        },
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.METRIC_ADDED
    assert changes[0].details["metric_name"] == "system.cpu.usage"


def test_metric_removed():
    """Test detecting removed metric."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "metrics": {
                            "system.cpu.usage": {
                                "description": "CPU usage",
                                "unit": "%",
                            }
                        },
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "otlp", "metrics": {}},
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.METRIC_REMOVED


def test_metric_modified():
    """Test detecting modified metric."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "metrics": {
                            "system.cpu.usage": {
                                "description": "CPU usage",
                                "unit": "%",
                            }
                        },
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {
                        "type": "otlp",
                        "metrics": {
                            "system.cpu.usage": {
                                "description": "CPU utilization",
                                "unit": "%",
                            }
                        },
                    },
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 1
    assert changes[0].change_type == ChangeType.METRIC_MODIFIED


def test_multiple_changes():
    """Test detecting multiple changes at once."""
    old_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "otlp"},
                }
            ],
            "processor": [],
            "exporter": [],
        },
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {
                    "name": "otlpreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "otlp"},
                },
                {
                    "name": "jaegerreceiver",
                    "has_metadata": True,
                    "metadata": {"type": "jaeger"},
                },
            ],
            "processor": [
                {
                    "name": "batchprocessor",
                    "has_metadata": True,
                    "metadata": {"type": "batch"},
                }
            ],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    changes = detector.detect_all_changes()

    assert len(changes) == 2
    assert any(c.component_name == "jaegerreceiver" for c in changes)
    assert any(c.component_name == "batchprocessor" for c in changes)


def test_get_changes_by_type():
    """Test filtering changes by type."""
    old_inventory = {
        "repository": "test",
        "components": {"receiver": [], "processor": [], "exporter": []},
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {"name": "otlpreceiver", "has_metadata": True, "metadata": {"type": "otlp"}}
            ],
            "processor": [
                {
                    "name": "batchprocessor",
                    "has_metadata": True,
                    "metadata": {"type": "batch"},
                }
            ],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    detector.detect_all_changes()

    added = detector.get_changes_by_type(ChangeType.COMPONENT_ADDED)
    assert len(added) == 2


def test_get_changes_summary():
    """Test getting change summary."""
    old_inventory = {
        "repository": "test",
        "components": {"receiver": [], "processor": [], "exporter": []},
    }

    new_inventory = {
        "repository": "test",
        "components": {
            "receiver": [
                {"name": "otlpreceiver", "has_metadata": True, "metadata": {"type": "otlp"}}
            ],
            "processor": [
                {
                    "name": "batchprocessor",
                    "has_metadata": True,
                    "metadata": {"type": "batch"},
                }
            ],
            "exporter": [],
        },
    }

    detector = ChangeDetector(old_inventory, new_inventory)
    detector.detect_all_changes()

    summary = detector.get_changes_summary()
    assert summary["component_added"] == 2


def test_change_to_dict():
    """Test converting change to dictionary."""
    change = Change(
        change_type=ChangeType.COMPONENT_ADDED,
        component_type="receiver",
        component_name="otlpreceiver",
        description="New receiver added",
        new_value={"type": "otlp"},
    )

    change_dict = change.to_dict()
    assert change_dict["change_type"] == "component_added"
    assert change_dict["component_name"] == "otlpreceiver"
    assert change_dict["description"] == "New receiver added"
