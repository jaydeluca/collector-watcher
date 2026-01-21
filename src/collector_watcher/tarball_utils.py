"""Utilities for downloading and extracting GitHub release tarballs."""

import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from github.GitRelease import GitRelease


def download_and_extract_release(release: GitRelease, github_token: str | None = None) -> str:
    """
    Download and extract a GitHub release tarball to a temporary directory.

    Args:
        release: GitHub release object
        github_token: Optional GitHub token for authentication

    Returns:
        Path to the extracted repository directory

    Raises:
        Exception: If download or extraction fails
    """
    tarball_url = release.tarball_url

    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix=f"otel-scan-{release.tag_name}-")

    try:
        # Download the tarball with authentication if token provided
        request = Request(tarball_url)
        if github_token:
            request.add_header("Authorization", f"token {github_token}")

        with urlopen(request) as response:
            # Extract directly from the stream
            with tarfile.open(fileobj=response, mode="r|gz") as tar:
                tar.extractall(path=temp_dir)

        # Find the extracted directory (GitHub creates a top-level dir like "open-telemetry-repo-name-abc123")
        extracted_dirs = list(Path(temp_dir).iterdir())
        if len(extracted_dirs) != 1:
            raise ValueError(f"Expected one extracted directory, found {len(extracted_dirs)}")

        repo_path = str(extracted_dirs[0])
        return repo_path

    except Exception:
        # Clean up on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def cleanup_extracted_release(repo_path: str) -> None:
    """
    Clean up an extracted release directory.

    Args:
        repo_path: Path to the extracted repository directory
    """
    # Get the parent temp directory
    temp_dir = Path(repo_path).parent
    shutil.rmtree(temp_dir, ignore_errors=True)
