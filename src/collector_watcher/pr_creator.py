"""GitHub Pull Request creator for documentation updates."""

import shutil
from datetime import datetime
from pathlib import Path

from git import Repo
from github import Auth, Github
from github.GithubException import GithubException


class PRCreator:
    """Creates GitHub Pull Requests for documentation updates."""

    def __init__(
        self,
        github_token: str,
        repo_owner: str = "open-telemetry",
        repo_name: str = "opentelemetry.io",
        fork_owner: str | None = None,
    ):
        """
        Initialize the PR creator.

        Args:
            github_token: GitHub personal access token
            repo_owner: Owner of the target repository
            repo_name: Name of the target repository
            fork_owner: Owner of the fork (defaults to authenticated user)
        """
        auth = Auth.Token(github_token)
        self.github = Github(auth=auth)
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.fork_owner = fork_owner or self.github.get_user().login
        self.github_token = github_token

        # Get repository objects
        self.upstream_repo = self.github.get_repo(f"{repo_owner}/{repo_name}")
        self.fork_repo = self.github.get_repo(f"{self.fork_owner}/{repo_name}")

    def clone_or_update_repo(self, local_path: str | Path, base_branch: str = "main") -> Repo:
        """
        Clone repository or update if it already exists.

        Args:
            local_path: Local path to clone to
            base_branch: Base branch to checkout

        Returns:
            GitPython Repo object
        """
        local_path = Path(local_path)

        if local_path.exists():
            # Repository exists, update it
            repo = Repo(local_path)
            origin = repo.remotes.origin

            # Fetch latest changes
            origin.fetch()

            # Checkout base branch
            if base_branch not in repo.heads:
                # Create local branch tracking remote
                repo.create_head(base_branch, origin.refs[base_branch])

            repo.heads[base_branch].checkout()

            # Pull latest changes
            origin.pull(base_branch)

            return repo
        else:
            # Clone repository
            clone_url = self.fork_repo.clone_url

            # Use token for authentication in clone URL
            clone_url_with_auth = clone_url.replace(
                "https://", f"https://{self.fork_owner}:{self.github_token}@"
            )

            repo = Repo.clone_from(clone_url_with_auth, local_path, branch=base_branch)

            # Add upstream remote if it doesn't exist
            if "upstream" not in [remote.name for remote in repo.remotes]:
                upstream_url = self.upstream_repo.clone_url
                repo.create_remote("upstream", upstream_url)

            return repo

    def create_feature_branch(self, repo: Repo, branch_name: str | None = None) -> str:
        """
        Create and checkout a new feature branch.

        Args:
            repo: GitPython Repo object
            branch_name: Name of the branch (auto-generated if None)

        Returns:
            Branch name
        """
        if branch_name is None:
            # Generate branch name based on date
            date_str = datetime.now().strftime("%Y-%m-%d")
            branch_name = f"auto-update-components-{date_str}"

        # Delete branch if it already exists
        if branch_name in repo.heads:
            repo.delete_head(branch_name, force=True)

        # Create and checkout new branch
        repo.create_head(branch_name)
        repo.heads[branch_name].checkout()

        return branch_name

    def commit_changes(
        self,
        repo: Repo,
        file_paths: list[str | Path],
        commit_message: str,
        author_name: str = "collector-watcher[bot]",
        author_email: str = "collector-watcher[bot]@users.noreply.github.com",
    ) -> bool:
        """
        Stage and commit changes.

        Args:
            repo: GitPython Repo object
            file_paths: List of file paths to stage
            commit_message: Commit message
            author_name: Git author name
            author_email: Git author email

        Returns:
            True if changes were committed, False if no changes to commit
        """
        # Stage files
        for file_path in file_paths:
            repo.index.add([str(file_path)])

        # Check if there are changes to commit
        if not repo.index.diff("HEAD"):
            return False

        # Configure git identity
        with repo.config_writer() as config:
            config.set_value("user", "name", author_name)
            config.set_value("user", "email", author_email)

        # Commit changes
        repo.index.commit(commit_message)

        return True

    def push_to_fork(self, repo: Repo, branch_name: str) -> None:
        """
        Push feature branch to fork.

        Args:
            repo: GitPython Repo object
            branch_name: Branch name to push
        """
        origin = repo.remotes.origin

        # Set up authentication in push URL
        push_url = f"https://{self.fork_owner}:{self.github_token}@github.com/{self.fork_owner}/{self.repo_name}.git"

        # Update origin URL with authentication
        with repo.config_writer() as config:
            config.set_value('remote "origin"', "url", push_url)

        # Push branch
        origin.push(refspec=f"{branch_name}:{branch_name}", force=True)

    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        dry_run: bool = False,
    ) -> dict | None:
        """
        Create a pull request from fork to upstream.

        Args:
            title: PR title
            body: PR body/description
            head_branch: Head branch (in fork)
            base_branch: Base branch (in upstream)
            dry_run: If True, don't create PR, just return metadata

        Returns:
            PR metadata dict or None
        """
        if dry_run:
            return {
                "number": None,
                "url": "DRY_RUN",
                "title": title,
                "body": body,
                "head": f"{self.fork_owner}:{head_branch}",
                "base": base_branch,
            }

        try:
            # Check for existing open PRs with same head
            existing_prs = self.upstream_repo.get_pulls(
                state="open", head=f"{self.fork_owner}:{head_branch}", base=base_branch
            )

            for pr in existing_prs:
                # Close existing PR
                pr.edit(state="closed")
                print(f"  🔄 Closed existing PR #{pr.number}: {pr.title}")

            # Create new PR
            pr = self.upstream_repo.create_pull(
                title=title,
                body=body,
                head=f"{self.fork_owner}:{head_branch}",
                base=base_branch,
            )

            return {
                "number": pr.number,
                "url": pr.html_url,
                "title": title,
            }

        except GithubException as e:
            print(f"  ❌ Failed to create pull request: {e}")
            return None

    def cleanup_local_repo(self, local_path: str | Path) -> None:
        """
        Remove local repository clone.

        Args:
            local_path: Path to local repository
        """
        local_path = Path(local_path)
        if local_path.exists():
            shutil.rmtree(local_path)


def generate_commit_message(added: list[str], removed: list[str], updated: list[str]) -> str:
    """
    Generate commit message for documentation changes.

    Args:
        added: List of added components
        removed: List of removed components
        updated: List of updated components

    Returns:
        Formatted commit message
    """
    lines = ["docs: Update OpenTelemetry Collector component pages", ""]

    if added or removed or updated:
        lines.append("Changes detected in latest scan:")
        if added:
            lines.append(f"- Added: {', '.join(added)}")
        if removed:
            lines.append(f"- Removed: {', '.join(removed)}")
        if updated:
            lines.append(f"- Updated: {len(updated)} component(s) with stability changes")

    lines.extend(["", "🤖 Generated by collector-watcher"])

    return "\n".join(lines)


def generate_pr_body(
    added: list[str], removed: list[str], updated: list[str], files: list[str]
) -> str:
    """
    Generate PR body/description for documentation changes.

    Args:
        added: List of added components (format: "type/name")
        removed: List of removed components
        updated: List of updated components
        files: List of files changed

    Returns:
        Formatted PR body in markdown
    """
    lines = [
        "## Automated Component Update",
        "",
        "This PR updates the OpenTelemetry Collector component documentation based on the latest scan of opentelemetry-collector-contrib.",
        "",
        "### Summary",
    ]

    if added:
        lines.append(f"- **Added**: {len(added)} new component(s)")
    if removed:
        lines.append(f"- **Removed**: {len(removed)} component(s)")
    if updated:
        lines.append(f"- **Updated**: {len(updated)} component(s) with stability changes")

    if not (added or removed or updated):
        lines.append("- No component changes, refreshing documentation")

    lines.append("")
    lines.append("### Detailed Changes")
    lines.append("")

    if added:
        lines.append("#### Added Components")
        for component in added:
            lines.append(f"- **{component}**")
        lines.append("")

    if removed:
        lines.append("#### Removed Components")
        for component in removed:
            lines.append(f"- **{component}**")
        lines.append("")

    if updated:
        lines.append("#### Updated Components")
        for component in updated:
            lines.append(f"- **{component}**")
        lines.append("")

    lines.append("### Generated Files")
    for file in sorted(files):
        # Extract just the filename from path
        filename = Path(file).name
        lines.append(f"- `content/en/docs/collector/components/{filename}`")

    lines.extend(
        [
            "",
            "---",
            "🤖 Generated with [collector-watcher](https://github.com/jaydeluca/collector-watcher)",
        ]
    )

    return "\n".join(lines)
