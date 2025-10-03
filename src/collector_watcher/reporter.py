"""GitHub issue reporting for component changes."""

from github import Auth, Github
from github.GithubException import GithubException

from .detector import Change, ChangeType


class IssueReporter:
    """Creates GitHub issues for detected changes."""

    def __init__(self, github_token: str, repo_name: str = "jaydeluca/collector-watcher"):
        """
        Initialize the reporter.

        Args:
            github_token: GitHub personal access token
            repo_name: Repository name in format "owner/repo"
        """
        auth = Auth.Token(github_token)
        self.github = Github(auth=auth)
        self.repo = self.github.get_repo(repo_name)
        self.repo_name = repo_name

    def create_issues_for_changes(self, changes: list[Change], dry_run: bool = False) -> list[dict]:
        """
        Create GitHub issues for a list of changes.

        Args:
            changes: List of Change objects
            dry_run: If True, don't actually create issues, just return what would be created

        Returns:
            List of created issue metadata (number, url, title)
        """
        created_issues = []

        for change in changes:
            issue_data = self._create_issue_for_change(change, dry_run)
            if issue_data:
                created_issues.append(issue_data)

        return created_issues

    def _create_issue_for_change(self, change: Change, dry_run: bool = False) -> dict | None:
        """
        Create a single GitHub issue for a change.

        Args:
            change: Change object
            dry_run: If True, don't actually create the issue

        Returns:
            Issue metadata dict or None if skipped
        """
        title = self._format_issue_title(change)
        body = self._format_issue_body(change)
        labels = self._get_labels_for_change(change)

        if dry_run:
            return {
                "number": None,
                "url": "DRY_RUN",
                "title": title,
                "body": body,
                "labels": labels,
            }

        try:
            # Check for duplicate issues
            if self._is_duplicate_issue(title):
                print(f"  ⏭️  Skipping duplicate issue: {title}")
                return None

            issue = self.repo.create_issue(title=title, body=body, labels=labels)

            return {
                "number": issue.number,
                "url": issue.html_url,
                "title": title,
                "labels": labels,
            }

        except GithubException as e:
            print(f"  ❌ Failed to create issue for {change.description}: {e}")
            return None

    def _format_issue_title(self, change: Change) -> str:
        """
        Format issue title based on change type.

        Args:
            change: Change object

        Returns:
            Formatted issue title
        """
        component_path = f"{change.component_type}/{change.component_name}"

        if change.change_type == ChangeType.COMPONENT_ADDED:
            return f"[New Component] {component_path}"
        elif change.change_type == ChangeType.COMPONENT_REMOVED:
            return f"[Component Removed] {component_path}"
        elif change.change_type == ChangeType.METADATA_ADDED:
            return f"[Metadata Added] {component_path}"
        elif change.change_type == ChangeType.METADATA_REMOVED:
            return f"[Metadata Removed] {component_path}"
        elif change.change_type == ChangeType.STABILITY_CHANGED:
            return f"[Stability Change] {component_path}"
        elif change.change_type == ChangeType.ATTRIBUTE_ADDED:
            attr_name = change.details.get("attribute_name", "unknown")
            return f"[Attribute Added] {component_path} - {attr_name}"
        elif change.change_type == ChangeType.ATTRIBUTE_REMOVED:
            attr_name = change.details.get("attribute_name", "unknown")
            return f"[Attribute Removed] {component_path} - {attr_name}"
        elif change.change_type == ChangeType.ATTRIBUTE_MODIFIED:
            attr_name = change.details.get("attribute_name", "unknown")
            return f"[Attribute Modified] {component_path} - {attr_name}"
        elif change.change_type == ChangeType.METRIC_ADDED:
            metric_name = change.details.get("metric_name", "unknown")
            return f"[Metric Added] {component_path} - {metric_name}"
        elif change.change_type == ChangeType.METRIC_REMOVED:
            metric_name = change.details.get("metric_name", "unknown")
            return f"[Metric Removed] {component_path} - {metric_name}"
        elif change.change_type == ChangeType.METRIC_MODIFIED:
            metric_name = change.details.get("metric_name", "unknown")
            return f"[Metric Modified] {component_path} - {metric_name}"
        else:
            return f"[Component Change] {component_path}"

    def _format_issue_body(self, change: Change) -> str:
        """
        Format issue body with detailed change information.

        Args:
            change: Change object

        Returns:
            Formatted issue body in Markdown
        """
        component_path = f"{change.component_type}/{change.component_name}"
        link = f"https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/{component_path}"

        body = f"""## Component Change Detected

**Component:** `{component_path}`
**Change Type:** {change.change_type.value.replace("_", " ").title()}
**Link:** {link}

### Description
{change.description}
"""

        # Add old/new value details if present
        if change.old_value is not None or change.new_value is not None:
            body += "\n### Details\n"

            if change.old_value is not None:
                body += f"\n**Previous:**\n```yaml\n{self._format_value(change.old_value)}\n```\n"

            if change.new_value is not None:
                body += f"\n**Current:**\n```yaml\n{self._format_value(change.new_value)}\n```\n"

        # Add additional details if present
        if change.details:
            body += "\n### Additional Information\n"
            for key, value in change.details.items():
                body += f"- **{key}:** `{value}`\n"

        body += "\n---\n*This issue was automatically generated by the collector-watcher bot.*"

        return body

    def _format_value(self, value) -> str:
        """Format a value for display in issue body."""
        if isinstance(value, dict):
            import yaml

            return yaml.dump(value, default_flow_style=False, sort_keys=False).strip()
        elif isinstance(value, list):
            return "\n".join(f"- {item}" for item in value)
        else:
            return str(value)

    def _get_labels_for_change(self, change: Change) -> list[str]:
        """
        Get appropriate labels for a change.

        Args:
            change: Change object

        Returns:
            List of label names
        """
        labels = ["component-change"]

        # Add component type label
        labels.append(f"component:{change.component_type}")

        # Add change type specific labels
        if change.change_type in [ChangeType.COMPONENT_ADDED, ChangeType.METADATA_ADDED]:
            labels.append("addition")
        elif change.change_type in [ChangeType.COMPONENT_REMOVED, ChangeType.METADATA_REMOVED]:
            labels.append("removal")
        elif change.change_type == ChangeType.STABILITY_CHANGED:
            labels.append("stability")
        elif "ATTRIBUTE" in change.change_type.name:
            labels.append("attribute")
        elif "METRIC" in change.change_type.name:
            labels.append("metric")

        return labels

    def _is_duplicate_issue(self, title: str) -> bool:
        """
        Check if an issue with the same title already exists (open issues only).

        Args:
            title: Issue title to check

        Returns:
            True if duplicate found
        """
        try:
            # Search for open issues with exact title match
            issues = self.repo.get_issues(state="open")
            for issue in issues:
                if issue.title == title:
                    return True
            return False
        except GithubException:
            # If we can't check, assume not duplicate to avoid missing issues
            return False

    def close(self):
        """Close the GitHub connection."""
        self.github.close()
