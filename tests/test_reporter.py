"""Tests for GitHub issue reporter."""

from unittest.mock import Mock, patch

import pytest

from collector_watcher.detector import Change, ChangeType
from collector_watcher.reporter import IssueReporter


@pytest.fixture
def mock_github():
    """Mock GitHub API."""
    with patch("collector_watcher.reporter.Github") as mock_gh:
        mock_repo = Mock()
        mock_repo.create_issue = Mock(
            return_value=Mock(number=123, html_url="https://github.com/test/repo/issues/123")
        )
        mock_repo.get_issues = Mock(return_value=[])
        mock_gh.return_value.get_repo.return_value = mock_repo
        yield mock_gh, mock_repo


def test_reporter_initialization(mock_github):
    """Test reporter initialization."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token", "test/repo")

    assert reporter.repo == mock_repo
    assert reporter.repo_name == "test/repo"


def test_format_title_component_added(mock_github):
    """Test formatting title for component addition."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.COMPONENT_ADDED,
        component_type="receiver",
        component_name="newreceiver",
        description="New receiver added",
    )

    title = reporter._format_issue_title(change)
    assert title == "[New Component] receiver/newreceiver"


def test_format_title_stability_changed(mock_github):
    """Test formatting title for stability change."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.STABILITY_CHANGED,
        component_type="receiver",
        component_name="otlpreceiver",
        description="Stability changed",
    )

    title = reporter._format_issue_title(change)
    assert title == "[Stability Change] receiver/otlpreceiver"


def test_format_title_attribute_added(mock_github):
    """Test formatting title for attribute addition."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.ATTRIBUTE_ADDED,
        component_type="receiver",
        component_name="otlpreceiver",
        description="Attribute added",
        details={"attribute_name": "direction"},
    )

    title = reporter._format_issue_title(change)
    assert title == "[Attribute Added] receiver/otlpreceiver - direction"


def test_format_title_metric_modified(mock_github):
    """Test formatting title for metric modification."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.METRIC_MODIFIED,
        component_type="receiver",
        component_name="otlpreceiver",
        description="Metric modified",
        details={"metric_name": "system.cpu.usage"},
    )

    title = reporter._format_issue_title(change)
    assert title == "[Metric Modified] receiver/otlpreceiver - system.cpu.usage"


def test_format_body_with_old_new_values(mock_github):
    """Test formatting issue body with old and new values."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.STABILITY_CHANGED,
        component_type="receiver",
        component_name="otlpreceiver",
        description="Stability changed from beta to stable",
        old_value={"beta": ["metrics"]},
        new_value={"stable": ["metrics"]},
    )

    body = reporter._format_issue_body(change)

    assert "receiver/otlpreceiver" in body
    assert "Stability Changed" in body
    assert "Previous:" in body
    assert "Current:" in body
    assert "beta" in body
    assert "stable" in body
    assert "https://github.com/open-telemetry/opentelemetry-collector-contrib" in body


def test_format_body_with_details(mock_github):
    """Test formatting issue body with additional details."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.ATTRIBUTE_ADDED,
        component_type="receiver",
        component_name="otlpreceiver",
        description="Attribute added",
        details={"attribute_name": "direction", "type": "string"},
    )

    body = reporter._format_issue_body(change)

    assert "Additional Information" in body
    assert "attribute_name" in body
    assert "direction" in body


def test_get_labels_for_component_added(mock_github):
    """Test getting labels for component addition."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.COMPONENT_ADDED,
        component_type="receiver",
        component_name="newreceiver",
        description="New receiver added",
    )

    labels = reporter._get_labels_for_change(change)

    assert "component-change" in labels
    assert "component:receiver" in labels
    assert "addition" in labels


def test_get_labels_for_stability_change(mock_github):
    """Test getting labels for stability change."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.STABILITY_CHANGED,
        component_type="processor",
        component_name="batchprocessor",
        description="Stability changed",
    )

    labels = reporter._get_labels_for_change(change)

    assert "component-change" in labels
    assert "component:processor" in labels
    assert "stability" in labels


def test_get_labels_for_metric_change(mock_github):
    """Test getting labels for metric change."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.METRIC_ADDED,
        component_type="receiver",
        component_name="otlpreceiver",
        description="Metric added",
    )

    labels = reporter._get_labels_for_change(change)

    assert "component-change" in labels
    assert "component:receiver" in labels
    assert "metric" in labels


def test_create_issue_dry_run(mock_github):
    """Test creating issue in dry run mode."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.COMPONENT_ADDED,
        component_type="receiver",
        component_name="newreceiver",
        description="New receiver added",
    )

    result = reporter._create_issue_for_change(change, dry_run=True)

    assert result is not None
    assert result["number"] is None
    assert result["url"] == "DRY_RUN"
    assert result["title"] == "[New Component] receiver/newreceiver"
    assert "component-change" in result["labels"]

    # Should not actually create issue
    mock_repo.create_issue.assert_not_called()


def test_create_issue_for_real(mock_github):
    """Test actually creating an issue."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.COMPONENT_ADDED,
        component_type="receiver",
        component_name="newreceiver",
        description="New receiver added",
    )

    result = reporter._create_issue_for_change(change, dry_run=False)

    assert result is not None
    assert result["number"] == 123
    assert "github.com" in result["url"]

    # Should have called create_issue
    mock_repo.create_issue.assert_called_once()


def test_duplicate_issue_detection(mock_github):
    """Test duplicate issue detection."""
    mock_gh, mock_repo = mock_github

    # Mock existing issue
    existing_issue = Mock()
    existing_issue.title = "[New Component] receiver/existingreceiver"
    mock_repo.get_issues.return_value = [existing_issue]

    reporter = IssueReporter("fake-token")

    change = Change(
        change_type=ChangeType.COMPONENT_ADDED,
        component_type="receiver",
        component_name="existingreceiver",
        description="New receiver added",
    )

    result = reporter._create_issue_for_change(change, dry_run=False)

    # Should skip duplicate
    assert result is None
    mock_repo.create_issue.assert_not_called()


def test_create_issues_for_multiple_changes(mock_github):
    """Test creating issues for multiple changes."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    changes = [
        Change(
            change_type=ChangeType.COMPONENT_ADDED,
            component_type="receiver",
            component_name="receiver1",
            description="Receiver 1 added",
        ),
        Change(
            change_type=ChangeType.COMPONENT_ADDED,
            component_type="receiver",
            component_name="receiver2",
            description="Receiver 2 added",
        ),
    ]

    results = reporter.create_issues_for_changes(changes, dry_run=True)

    assert len(results) == 2
    assert results[0]["title"] == "[New Component] receiver/receiver1"
    assert results[1]["title"] == "[New Component] receiver/receiver2"


def test_format_value_dict(mock_github):
    """Test formatting dictionary values."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    value = {"stability": {"stable": ["metrics"]}}
    formatted = reporter._format_value(value)

    assert "stability" in formatted
    assert "stable" in formatted
    assert "metrics" in formatted


def test_format_value_list(mock_github):
    """Test formatting list values."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    value = ["metrics", "traces", "logs"]
    formatted = reporter._format_value(value)

    assert "- metrics" in formatted
    assert "- traces" in formatted
    assert "- logs" in formatted


def test_format_value_string(mock_github):
    """Test formatting string values."""
    mock_gh, mock_repo = mock_github
    reporter = IssueReporter("fake-token")

    value = "simple string"
    formatted = reporter._format_value(value)

    assert formatted == "simple string"
