
import re
from pathlib import Path

import git


HUNK_PATTERN = re.compile(
    r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@"
)


def detect_changed_functions(repo_root, project_root, functions):
    """
    Compare tracked working-tree changes against HEAD.

    Returns changed files, functions matched to changed lines,
    and files whose changes could not be mapped to a function.
    """
    repo_path = Path(repo_root).resolve()
    project_path = Path(project_root).resolve()

    repo = git.Repo(repo_path, search_parent_directories=True)

    if repo.head.is_detached and not repo.head.is_valid():
        raise ValueError("Git repository has no valid HEAD commit.")

    relative_project = project_path.relative_to(repo.working_tree_dir)

    changed_files_output = repo.git.diff(
        "HEAD",
        "--name-only",
        "--",
        relative_project.as_posix(),
    )

    changed_files = sorted(
        line.strip()
        for line in changed_files_output.splitlines()
        if line.strip()
    )

    matched_functions = set()
    unmapped_files = []

    for relative_file in changed_files:
        file_path = (Path(repo.working_tree_dir) / relative_file).resolve()

        if file_path.suffix != ".py" or not file_path.exists():
            unmapped_files.append(relative_file)
            continue

        diff_output = repo.git.diff(
            "HEAD",
            "--unified=0",
            "--",
            relative_file,
        )

        changed_lines = set()

        for line in diff_output.splitlines():
            match = HUNK_PATTERN.search(line)
            if not match:
                continue

            start = int(match.group(1))
            count = int(match.group(2) or 1)

            if count == 0:
                continue

            changed_lines.update(range(start, start + count))

        file_functions = [
            (name, details)
            for name, details in functions.items()
            if Path(details["file"]).resolve() == file_path
        ]

        file_matches = {
            name
            for name, details in file_functions
            if any(
                details["line"] <= line <= details["end_line"]
                for line in changed_lines
            )
        }

        matched_functions.update(file_matches)

        if not file_matches:
            unmapped_files.append(relative_file)

    return {
        "changed_files": changed_files,
        "changed_functions": sorted(matched_functions),
        "unmapped_files": sorted(set(unmapped_files)),
    }
