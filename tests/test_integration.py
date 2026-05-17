import pytest
import os
import shutil
import glob
import pexpect
import sys


@pytest.fixture(scope="module")
def setup_teardown_corporate_reports_dir():
    """Fixture to create and clean up the corporate_reports directory."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    test_dir = os.path.join(project_root, "corporate_reports")
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    yield test_dir  # Yield the path for use in the test
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


def test_full_corporate_consultant_pipeline(setup_teardown_corporate_reports_dir):
    """Tests the end-to-end execution of the corporate_consultant agent with live API calls."""
    company_name = "Apple Inc."
    ticker = "AAPL"
    user_input = f"{company_name}, {ticker}"
    corporate_reports_dir = setup_teardown_corporate_reports_dir

    # Construct the command to run the agent with piped input
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    command = [
        sys.executable,
        os.path.join(project_root, ".venv", "bin", "adk"),
        "run",
        "stock_intelligence_agent",
    ]

    env = os.environ.copy()
    env["MODEL"] = "gemini-2.5-flash"

    child = pexpect.spawn(
        command[0],
        command[1:],
        cwd=project_root,
        env=env,
        encoding="utf-8",
        timeout=120,
    )

    child.expect(r"\[user\]:")
    child.sendline(user_input)

    child.expect(r"\[user\]:")

    child.sendline("exit")
    child.expect(pexpect.EOF)

    md_files = glob.glob(os.path.join(corporate_reports_dir, "*.md"))
    expected_filename = (
        os.path.basename(md_files[0]) if md_files else "apple_biography.md"
    )

    report_path = os.path.join(corporate_reports_dir, expected_filename)

    assert os.path.exists(
        report_path
    ), f"Report file {expected_filename} was not created."

    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    print(f"Report content preview: {report_content[:500]}...")

    assert "EXECUTIVE SUMMARY" in report_content
    assert "HISTORICAL MILESTONES" in report_content
    assert "FINANCIAL DATA POINTS" in report_content
    assert company_name in report_content  # Ensure company name is in the report
    assert (
        "largest monthly increase".lower() in report_content.lower()
    )  # Check for specific phrasing from new prompt
    assert (
        "largest monthly decrease".lower() in report_content.lower()
    )  # Check for specific phrasing from new prompt
