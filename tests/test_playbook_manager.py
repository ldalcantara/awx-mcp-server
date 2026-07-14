"""Unit tests for playbook_manager (no live ansible; tmp workspaces only).

Every call passes an explicit tmp_path workspace so nothing touches the real
~/.awx-mcp; subprocess execution is mocked.
"""

import asyncio

from awx_mcp_server import playbook_manager as pm

PLAY = "---\n- hosts: all\n  tasks:\n    - ansible.builtin.ping:\n"


# ---- create_playbook ----


def test_create_playbook_from_yaml_string(tmp_path):
    res = pm.create_playbook("deploy", PLAY, workspace=str(tmp_path))
    assert res["status"] == "created"
    assert res["name"] == "deploy.yml"  # extension added
    assert res["plays"] == 1
    assert (tmp_path / "deploy.yml").read_text() == PLAY


def test_create_playbook_wraps_single_play_dict(tmp_path):
    play = {"hosts": "all", "tasks": []}
    res = pm.create_playbook("one.yml", play, workspace=str(tmp_path))
    assert res["status"] == "created"
    assert res["plays"] == 1


def test_create_playbook_rejects_invalid_yaml(tmp_path):
    res = pm.create_playbook("bad.yml", "not: [valid", workspace=str(tmp_path))
    assert res["status"] == "error"
    assert "Invalid YAML" in res["message"]
    assert not (tmp_path / "bad.yml").exists()


def test_create_playbook_rejects_empty_and_scalar_yaml(tmp_path):
    assert pm.create_playbook("e.yml", "", workspace=str(tmp_path))["status"] == "error"
    res = pm.create_playbook("s.yml", "just a string", workspace=str(tmp_path))
    assert res["status"] == "error"
    assert "list of plays" in res["message"]


def test_create_playbook_rejects_wrong_type(tmp_path):
    res = pm.create_playbook("n.yml", 42, workspace=str(tmp_path))
    assert res["status"] == "error"


def test_create_playbook_overwrite_guard(tmp_path):
    assert (
        pm.create_playbook("x.yml", PLAY, workspace=str(tmp_path))["status"]
        == "created"
    )
    res = pm.create_playbook("x.yml", PLAY, workspace=str(tmp_path))
    assert res["status"] == "error"
    assert "already exists" in res["message"]
    res = pm.create_playbook("x.yml", PLAY, workspace=str(tmp_path), overwrite=True)
    assert res["status"] == "created"


# ---- validate_playbook (subprocess mocked) ----


class _FakeProc:
    def __init__(self, rc, out=b"", err=b""):
        self.returncode = rc
        self._out, self._err = out, err

    async def communicate(self):
        return self._out, self._err


def _install_fake_exec(monkeypatch, rc=0, out=b"", err=b"", raise_fnf=False):
    calls = {}

    async def fake_exec(*cmd, **kwargs):
        if raise_fnf:
            raise FileNotFoundError("ansible-playbook")
        calls["cmd"] = list(cmd)
        return _FakeProc(rc, out, err)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    return calls


async def test_validate_playbook_missing_file(tmp_path):
    res = await pm.validate_playbook("nope.yml", workspace=str(tmp_path))
    assert res["status"] == "error"
    assert "not found" in res["message"]


async def test_validate_playbook_valid(tmp_path, monkeypatch):
    pm.create_playbook("ok.yml", PLAY, workspace=str(tmp_path))
    calls = _install_fake_exec(monkeypatch, rc=0, out=b"playbook: ok.yml")
    res = await pm.validate_playbook("ok.yml", workspace=str(tmp_path))
    assert res["status"] == "valid"
    # syntax-check mode with a default localhost inventory
    assert "--syntax-check" in calls["cmd"]
    assert "localhost," in calls["cmd"]


async def test_validate_playbook_invalid_reports_errors(tmp_path, monkeypatch):
    pm.create_playbook("ok.yml", PLAY, workspace=str(tmp_path))
    _install_fake_exec(monkeypatch, rc=4, err=b"ERROR! the field 'hosts' is required")
    res = await pm.validate_playbook("ok.yml", workspace=str(tmp_path))
    assert res["status"] == "invalid"
    assert res["returncode"] == 4
    assert "hosts" in res["errors"]


async def test_validate_playbook_ansible_missing(tmp_path, monkeypatch):
    pm.create_playbook("ok.yml", PLAY, workspace=str(tmp_path))
    _install_fake_exec(monkeypatch, raise_fnf=True)
    res = await pm.validate_playbook("ok.yml", workspace=str(tmp_path))
    assert res["status"] == "error"
    assert "ansible-playbook not found" in res["message"]


# ---- role scaffolding + listings ----


def test_create_role_structure_scaffolds_standard_dirs(tmp_path):
    res = pm.create_role_structure("web", workspace=str(tmp_path))
    assert res["status"] == "created"
    role = tmp_path / "roles" / "web"
    for d in ("tasks", "handlers", "vars", "defaults", "meta"):
        assert (role / d / "main.yml").exists()
    # templates/files get no main.yml
    assert (role / "templates").is_dir()
    assert not (role / "templates" / "main.yml").exists()
    assert (role / "README.md").exists()
    # second call refuses to clobber
    assert pm.create_role_structure("web", workspace=str(tmp_path))["status"] == "error"


def test_create_role_structure_include_dirs_subset(tmp_path):
    res = pm.create_role_structure(
        "min", workspace=str(tmp_path), include_dirs=["tasks"]
    )
    assert res["directories"] == ["tasks"]
    assert (tmp_path / "roles" / "min" / "tasks" / "main.yml").exists()
    assert not (tmp_path / "roles" / "min" / "defaults").exists()


def test_list_playbooks_counts_plays_and_skips_temp(tmp_path):
    assert pm.list_playbooks(workspace=str(tmp_path))["count"] == 0
    pm.create_playbook("a.yml", PLAY, workspace=str(tmp_path))
    (tmp_path / "b.yml").write_text("not: [valid yaml")  # unparseable -> plays None
    (tmp_path / "_temp_scratch.yml").write_text(PLAY)  # skipped
    res = pm.list_playbooks(workspace=str(tmp_path))
    assert res["count"] == 2
    by_name = {p["name"]: p for p in res["playbooks"]}
    assert by_name["a.yml"]["plays"] == 1
    assert by_name["b.yml"]["plays"] is None
    assert "_temp_scratch.yml" not in by_name


def test_list_roles(tmp_path):
    assert pm.list_roles(workspace=str(tmp_path))["count"] == 0
    pm.create_role_structure("web", workspace=str(tmp_path))
    res = pm.list_roles(workspace=str(tmp_path))
    assert res["count"] == 1
    assert res["roles"][0]["name"] == "web"
    assert "tasks" in res["roles"][0]["directories"]
