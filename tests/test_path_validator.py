"""Tests for sky_claw.security.path_validator."""

from __future__ import annotations

import pathlib

import pytest

from sky_claw.security.path_validator import PathValidator, PathViolation, sandboxed_io


@pytest.fixture()
def tmp_sandbox(tmp_path: pathlib.Path) -> PathValidator:
    """Validator rooted at a temporary directory."""
    return PathValidator(roots=[tmp_path])


# ------------------------------------------------------------------
# Basic validation
# ------------------------------------------------------------------


class TestPathValidator:
    def test_path_inside_sandbox_accepted(
        self, tmp_sandbox: PathValidator, tmp_path: pathlib.Path
    ) -> None:
        child = tmp_path / "mods" / "skse"
        child.mkdir(parents=True)
        result = tmp_sandbox.validate(child)
        assert result == child.resolve()

    def test_path_outside_sandbox_rejected(
        self, tmp_sandbox: PathValidator
    ) -> None:
        with pytest.raises(PathViolation, match="outside all sandbox roots"):
            tmp_sandbox.validate("/etc/passwd")

    def test_traversal_dot_dot_rejected(
        self, tmp_sandbox: PathValidator, tmp_path: pathlib.Path
    ) -> None:
        sneaky = tmp_path / "mods" / ".." / ".." / "etc" / "passwd"
        with pytest.raises(PathViolation, match="traversal"):
            tmp_sandbox.validate(sneaky)

    def test_multiple_roots(self, tmp_path: pathlib.Path) -> None:
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        root_a.mkdir()
        root_b.mkdir()
        v = PathValidator(roots=[root_a, root_b])
        file_in_b = root_b / "test.txt"
        file_in_b.touch()
        assert v.validate(file_in_b) == file_in_b.resolve()

    def test_no_roots_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one"):
            PathValidator(roots=[])


# ------------------------------------------------------------------
# Decorator
# ------------------------------------------------------------------


class TestSandboxedIODecorator:
    def test_decorator_allows_valid_path(
        self, tmp_path: pathlib.Path
    ) -> None:
        @sandboxed_io(roots=[tmp_path])
        def write_file(path: pathlib.Path) -> str:
            return "ok"

        valid = tmp_path / "test.txt"
        valid.touch()
        assert write_file(valid) == "ok"

    def test_decorator_blocks_invalid_path(
        self, tmp_path: pathlib.Path
    ) -> None:
        @sandboxed_io(roots=[tmp_path])
        def write_file(path: pathlib.Path) -> str:
            return "ok"

        with pytest.raises(PathViolation):
            write_file(pathlib.Path("/etc/shadow"))

    def test_decorator_kwarg(self, tmp_path: pathlib.Path) -> None:
        @sandboxed_io(roots=[tmp_path], arg_name="target")
        def copy_file(target: pathlib.Path) -> str:
            return "copied"

        valid = tmp_path / "dest.dat"
        valid.touch()
        assert copy_file(target=valid) == "copied"
