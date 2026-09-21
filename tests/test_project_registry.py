"""Unit tests for project_registry (registry redirected to tmp_path).

REGISTRY_FILE is monkeypatched in every test so nothing reads or writes the
real ~/.awx-mcp/project_registry.json.
"""

import pytest
from awx_mcp_server import project_registry as pr


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "REGISTRY_FILE", tmp_path / "registry.json")


@pytest.fixture
def project_dir(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    return d


def test_register_rejects_missing_directory(tmp_path):
    res = pr.register_project("x", str(tmp_path / "nope"))
    assert res["status"] == "error"
    assert "Directory not found" in res["message"]


def test_register_first_project_becomes_default(project_dir):
    res = pr.register_project("app", str(project_dir))
    assert res["status"] == "registered"
    assert res["is_default"] is True
    assert res["project"]["scm_branch"] == "main"


def test_register_autodetects_inventory_playbook_and_scm(project_dir):
    (project_dir / "hosts").write_text("[all]\n")
    (project_dir / "site.yml").write_text("---\n- hosts: all\n")
    git = project_dir / ".git"
    git.mkdir()
    (git / "config").write_text(
        '[remote "origin"]\n\turl = git@github.test:me/app.git\n'
    )
    res = pr.register_project("app", str(project_dir))
    assert res["project"]["inventory"] == "hosts"
    assert res["project"]["default_playbook"] == "site.yml"
    assert res["project"]["scm_url"] == "git@github.test:me/app.git"


def test_second_project_keeps_default_unless_requested(project_dir, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    pr.register_project("first", str(project_dir))
    res = pr.register_project("second", str(other))
    assert res["is_default"] is False
    res = pr.register_project("second", str(other), set_default=True)
    assert res["is_default"] is True


def test_unregister_reassigns_default(project_dir, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    pr.register_project("a", str(project_dir))
    pr.register_project("b", str(other))
    assert pr.unregister_project("a") == {"status": "removed", "project": "a"}
    # default fell back to the remaining project
    assert pr.get_project()["project"]["name"] == "b"
    pr.unregister_project("b")
    assert pr.get_project()["status"] == "error"


def test_unregister_unknown_project(project_dir):
    res = pr.unregister_project("ghost")
    assert res["status"] == "error"


def test_list_projects_counts_playbooks_and_flags_default(project_dir):
    (project_dir / "site.yml").write_text("---\n- hosts: all\n")
    (project_dir / "deploy.yml").write_text("---\n- hosts: all\n")
    (project_dir / "requirements.yml").write_text("collections: []\n")  # excluded
    pr.register_project("app", str(project_dir))
    res = pr.list_projects()
    assert res["count"] == 1
    assert res["default"] == "app"
    info = res["projects"][0]
    assert info["exists"] is True
    assert info["is_default"] is True
    assert info["playbook_count"] == 2  # requirements.yml not counted


def test_get_project_by_name_and_default(project_dir):
    pr.register_project("app", str(project_dir))
    assert pr.get_project("app")["status"] == "found"
    assert pr.get_project()["status"] == "found"  # falls back to default
    assert pr.get_project("ghost")["status"] == "error"


def test_get_project_no_default_set():
    assert pr.get_project()["status"] == "error"
    assert "No default project" in pr.get_project()["message"]


def test_corrupt_registry_file_yields_fresh_registry(tmp_path):
    pr.REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    pr.REGISTRY_FILE.write_text("{not json")
    assert pr._load_registry() == {"projects": {}, "default": None}


def test_discover_playbooks_by_path_skips_support_files(project_dir):
    (project_dir / "site.yml").write_text("---\n- hosts: all\n  tasks: []\n")
    (project_dir / "requirements.yml").write_text("collections: []\n")
    roles = project_dir / "roles" / "r1" / "tasks"
    roles.mkdir(parents=True)
    (roles / "main.yml").write_text("---\n- hosts: all\n")  # under roles/ -> skipped
    res = pr.discover_playbooks(project_path=str(project_dir))
    assert res["status"] == "success"
    # only real playbooks (list of plays with hosts) count; support files and
    # anything under roles/ are excluded from the playbook list
    assert res["playbook_count"] == 1
    pb = res["playbooks"][0]
    assert pb["name"] == "site.yml"
    assert pb["relative_path"] == "site.yml"
    assert pb["plays"] == 1
    assert pb["hosts"] == "all"
    # the role is reported separately
    assert res["role_count"] == 1
    assert res["roles"][0]["name"] == "r1"
    assert "tasks" in res["roles"][0]["directories"]


def test_discover_playbooks_missing_dir(tmp_path):
    res = pr.discover_playbooks(project_path=str(tmp_path / "nope"))
    assert res["status"] == "error"
