"""Tests for changelog generator."""

from docs_automation.changelog_generator import ChangelogGenerator


def test_compare_component_type_new_component():
    """Test detecting newly added components."""
    gen = ChangelogGenerator()

    old_components = [
        {"name": "component1", "metadata": {}},
    ]

    new_components = [
        {"name": "component1", "metadata": {}},
        {"name": "component2", "metadata": {}},
    ]

    changes = gen.compare_component_type("receiver", old_components, new_components)

    assert changes["added"] == ["component2"]
    assert changes["removed"] == []
    assert changes["stability_changed"] == []
    assert changes["distribution_changed"] == []


def test_compare_component_type_removed_component():
    """Test detecting removed components."""
    gen = ChangelogGenerator()

    old_components = [
        {"name": "component1", "metadata": {}},
        {"name": "component2", "metadata": {}},
    ]

    new_components = [
        {"name": "component1", "metadata": {}},
    ]

    changes = gen.compare_component_type("receiver", old_components, new_components)

    assert changes["added"] == []
    assert changes["removed"] == ["component2"]
    assert changes["stability_changed"] == []
    assert changes["distribution_changed"] == []


def test_compare_component_type_stability_change():
    """Test detecting stability changes."""
    gen = ChangelogGenerator()

    old_components = [
        {
            "name": "component1",
            "metadata": {
                "status": {
                    "stability": {
                        "alpha": ["traces"],
                        "beta": ["metrics"],
                    }
                }
            },
        },
    ]

    new_components = [
        {
            "name": "component1",
            "metadata": {
                "status": {
                    "stability": {
                        "beta": ["traces", "metrics"],
                    }
                }
            },
        },
    ]

    changes = gen.compare_component_type("receiver", old_components, new_components)

    assert changes["added"] == []
    assert changes["removed"] == []
    assert len(changes["stability_changed"]) == 1
    assert changes["stability_changed"][0]["name"] == "component1"
    assert changes["stability_changed"][0]["old"] == {"traces": "alpha", "metrics": "beta"}
    assert changes["stability_changed"][0]["new"] == {"traces": "beta", "metrics": "beta"}


def test_compare_component_type_distribution_change():
    """Test detecting distribution changes."""
    gen = ChangelogGenerator()

    old_components = [
        {
            "name": "component1",
            "metadata": {
                "status": {
                    "distributions": ["contrib"],
                }
            },
        },
    ]

    new_components = [
        {
            "name": "component1",
            "metadata": {
                "status": {
                    "distributions": ["contrib", "k8s"],
                }
            },
        },
    ]

    changes = gen.compare_component_type("receiver", old_components, new_components)

    assert changes["added"] == []
    assert changes["removed"] == []
    assert changes["stability_changed"] == []
    assert len(changes["distribution_changed"]) == 1
    assert changes["distribution_changed"][0]["name"] == "component1"
    assert changes["distribution_changed"][0]["added"] == ["k8s"]
    assert changes["distribution_changed"][0]["removed"] == []


def test_compare_component_type_no_changes():
    """Test when there are no changes."""
    gen = ChangelogGenerator()

    components = [
        {
            "name": "component1",
            "metadata": {
                "status": {
                    "stability": {"alpha": ["traces"]},
                    "distributions": ["contrib"],
                }
            },
        },
    ]

    changes = gen.compare_component_type("receiver", components, components)

    assert changes["added"] == []
    assert changes["removed"] == []
    assert changes["stability_changed"] == []
    assert changes["distribution_changed"] == []


def test_compare_inventories():
    """Test comparing complete inventories."""
    gen = ChangelogGenerator()

    old_inventory = {
        "components": {
            "receiver": [
                {"name": "receiver1", "metadata": {}},
            ],
            "processor": [
                {"name": "processor1", "metadata": {}},
            ],
        }
    }

    new_inventory = {
        "components": {
            "receiver": [
                {"name": "receiver1", "metadata": {}},
                {"name": "receiver2", "metadata": {}},
            ],
            "processor": [
                {"name": "processor1", "metadata": {}},
            ],
        }
    }

    changes = gen.compare_inventories(old_inventory, new_inventory)

    assert "receiver" in changes
    assert changes["receiver"]["added"] == ["receiver2"]
    assert "processor" not in changes  # No changes in processor


def test_format_changes_markdown_new_components():
    """Test markdown formatting for new components."""
    gen = ChangelogGenerator()

    changes = {
        "receiver": {
            "added": ["newreceiver"],
            "removed": [],
            "stability_changed": [],
            "distribution_changed": [],
        }
    }

    markdown = gen.format_changes_markdown(changes)

    assert "## Summary of Changes" in markdown
    assert "### Receivers" in markdown
    assert "**New components:**" in markdown
    assert "`newreceiver`" in markdown


def test_format_changes_markdown_stability_changes():
    """Test markdown formatting for stability changes."""
    gen = ChangelogGenerator()

    changes = {
        "receiver": {
            "added": [],
            "removed": [],
            "stability_changed": [
                {
                    "name": "myreceiver",
                    "old": {"traces": "alpha"},
                    "new": {"traces": "beta"},
                }
            ],
            "distribution_changed": [],
        }
    }

    markdown = gen.format_changes_markdown(changes)

    assert "## Summary of Changes" in markdown
    assert "### Receivers" in markdown
    assert "**Stability changes:**" in markdown
    assert "`myreceiver`" in markdown
    assert "traces: alpha → beta" in markdown


def test_format_changes_markdown_no_changes():
    """Test markdown formatting when there are no changes."""
    gen = ChangelogGenerator()

    changes = {}

    markdown = gen.format_changes_markdown(changes)

    assert markdown == "No significant changes detected."


def test_format_changes_markdown_distribution_changes():
    """Test markdown formatting for distribution changes."""
    gen = ChangelogGenerator()

    changes = {
        "exporter": {
            "added": [],
            "removed": [],
            "stability_changed": [],
            "distribution_changed": [
                {
                    "name": "myexporter",
                    "added": ["k8s"],
                    "removed": [],
                }
            ],
        }
    }

    markdown = gen.format_changes_markdown(changes)

    assert "## Summary of Changes" in markdown
    assert "### Exporters" in markdown
    assert "**Distribution changes:**" in markdown
    assert "`myexporter`" in markdown
    assert "added to k8s" in markdown


def test_get_stability_summary():
    """Test extracting stability summary from component."""
    gen = ChangelogGenerator()

    component = {
        "name": "test",
        "metadata": {
            "status": {
                "stability": {
                    "alpha": ["traces"],
                    "beta": ["metrics", "logs"],
                }
            }
        },
    }

    stability = gen._get_stability_summary(component)

    assert stability == {
        "traces": "alpha",
        "metrics": "beta",
        "logs": "beta",
    }


def test_get_stability_summary_empty():
    """Test extracting stability from component without metadata."""
    gen = ChangelogGenerator()

    component = {"name": "test"}

    stability = gen._get_stability_summary(component)

    assert stability == {}


def test_get_distributions():
    """Test extracting distributions from component."""
    gen = ChangelogGenerator()

    component = {
        "name": "test",
        "metadata": {
            "status": {
                "distributions": ["contrib", "k8s"],
            }
        },
    }

    distributions = gen._get_distributions(component)

    assert distributions == {"contrib", "k8s"}


def test_get_distributions_empty():
    """Test extracting distributions from component without metadata."""
    gen = ChangelogGenerator()

    component = {"name": "test"}

    distributions = gen._get_distributions(component)

    assert distributions == set()


def test_connector_stability_skipped():
    """Test that connectors skip stability comparison."""
    gen = ChangelogGenerator()

    old_components = [
        {
            "name": "connector1",
            "metadata": {
                "status": {
                    "stability": {
                        "alpha": ["traces"],
                    }
                }
            },
        },
    ]

    new_components = [
        {
            "name": "connector1",
            "metadata": {
                "status": {
                    "stability": {
                        "beta": ["traces"],
                    }
                }
            },
        },
    ]

    changes = gen.compare_component_type("connector", old_components, new_components)

    # Connectors should skip stability comparison
    assert changes["stability_changed"] == []
