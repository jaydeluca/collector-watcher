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


def test_scanner_capability_change_filters_false_positives():
    """Test that components from new scanner capabilities are filtered out.

    When the old inventory didn't scan a subtype (e.g., encoding) at all,
    new components with that subtype should not be reported as "added"
    since they're false positives from scanner capability changes.
    """
    gen = ChangelogGenerator()

    # Old inventory has no encoding extensions (scanner didn't support them)
    old_components = [
        {"name": "healthcheckextension", "metadata": {}},
        {"name": "pprofextension", "metadata": {}},
    ]

    # New inventory has encoding extensions (scanner now supports them)
    new_components = [
        {"name": "healthcheckextension", "metadata": {}},
        {"name": "pprofextension", "metadata": {}},
        {"name": "newextension", "metadata": {}},  # Actually new
        {"name": "jsonencodingextension", "subtype": "encoding", "metadata": {}},
        {"name": "avroencondingextension", "subtype": "encoding", "metadata": {}},
    ]

    changes = gen.compare_component_type("extension", old_components, new_components)

    # Only "newextension" should be reported as added
    # Encoding extensions should be filtered out as scanner capability changes
    assert changes["added"] == ["newextension"]


def test_scanner_capability_change_preserves_real_additions_with_existing_subtype():
    """Test that when a subtype already existed, new components with that subtype are reported.

    If the old inventory already had some components with a subtype (e.g., observer),
    then new components with that same subtype should be reported as added.
    """
    gen = ChangelogGenerator()

    # Old inventory has some observer extensions
    old_components = [
        {"name": "healthcheckextension", "metadata": {}},
        {"name": "dockerobserver", "subtype": "observer", "metadata": {}},
    ]

    # New inventory has a new observer extension
    new_components = [
        {"name": "healthcheckextension", "metadata": {}},
        {"name": "dockerobserver", "subtype": "observer", "metadata": {}},
        {"name": "k8sobserver", "subtype": "observer", "metadata": {}},  # New observer
    ]

    changes = gen.compare_component_type("extension", old_components, new_components)

    # k8sobserver should be reported as added since observer subtype existed before
    assert changes["added"] == ["k8sobserver"]


def test_get_subtype():
    """Test extracting subtype from a component."""
    gen = ChangelogGenerator()

    component_with_subtype = {"name": "test", "subtype": "encoding", "metadata": {}}
    component_without_subtype = {"name": "test", "metadata": {}}

    assert gen._get_subtype(component_with_subtype) == "encoding"
    assert gen._get_subtype(component_without_subtype) is None


def test_get_subtypes_in_list():
    """Test extracting all subtypes from a list of components."""
    gen = ChangelogGenerator()

    components = [
        {"name": "comp1", "metadata": {}},
        {"name": "comp2", "subtype": "encoding", "metadata": {}},
        {"name": "comp3", "subtype": "observer", "metadata": {}},
        {"name": "comp4", "subtype": "encoding", "metadata": {}},
    ]

    subtypes = gen._get_subtypes_in_list(components)

    assert subtypes == {"encoding", "observer"}


def test_get_subtypes_in_list_empty():
    """Test extracting subtypes from components with no subtypes."""
    gen = ChangelogGenerator()

    components = [
        {"name": "comp1", "metadata": {}},
        {"name": "comp2", "metadata": {}},
    ]

    subtypes = gen._get_subtypes_in_list(components)

    assert subtypes == set()
