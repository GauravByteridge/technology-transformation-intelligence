"""Unit tests for the PromptManager."""

from pathlib import Path

import pytest

from app.ai.prompt_manager import PromptManager, PromptNotFoundError


@pytest.fixture
def prompt_manager() -> PromptManager:
    """Create a PromptManager pointing at the real prompts directory."""
    return PromptManager()


@pytest.fixture
def tmp_prompts_dir(tmp_path: Path) -> Path:
    """Create a temporary prompts directory with test templates."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Template with front-matter
    template = prompts_dir / "test_prompt_v1.md"
    template.write_text(
        "---\nversion: v1\nname: test_prompt\n---\n\n# Test Prompt\n\nHello, world.\n",
        encoding="utf-8",
    )

    # Template with different version
    template_v2 = prompts_dir / "test_prompt_v2.md"
    template_v2.write_text(
        "---\nversion: v2\nname: test_prompt\n---\n\n# Test Prompt V2\n\nUpdated content.\n",
        encoding="utf-8",
    )

    # Template without front-matter
    no_meta = prompts_dir / "plain_prompt_v1.md"
    no_meta.write_text("# Plain Prompt\n\nNo metadata here.\n", encoding="utf-8")

    return prompts_dir


class TestLoadPrompt:
    """Tests for PromptManager.load_prompt()."""

    def test_loads_system_prompt_v1(self, prompt_manager: PromptManager) -> None:
        """The default system_prompt_v1.md template loads successfully."""
        content = prompt_manager.load_prompt("system_prompt", "v1")

        assert "Technology Transformation Intelligence" in content
        assert "AI Assistant" in content
        assert "---" not in content  # Front-matter stripped

    def test_strips_front_matter(self, tmp_prompts_dir: Path) -> None:
        """Front-matter is removed from loaded template content."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)
        content = manager.load_prompt("test_prompt", "v1")

        assert "version:" not in content
        assert "name:" not in content
        assert "# Test Prompt" in content
        assert "Hello, world." in content

    def test_loads_different_versions(self, tmp_prompts_dir: Path) -> None:
        """Different versions of the same prompt can be loaded."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)

        v1 = manager.load_prompt("test_prompt", "v1")
        v2 = manager.load_prompt("test_prompt", "v2")

        assert "Hello, world." in v1
        assert "Updated content." in v2

    def test_defaults_to_v1(self, tmp_prompts_dir: Path) -> None:
        """Version defaults to 'v1' when not specified."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)
        content = manager.load_prompt("test_prompt")

        assert "Hello, world." in content

    def test_raises_on_missing_template(self, tmp_prompts_dir: Path) -> None:
        """PromptNotFoundError raised for non-existent templates."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)

        with pytest.raises(PromptNotFoundError) as exc_info:
            manager.load_prompt("nonexistent", "v99")

        assert exc_info.value.name == "nonexistent"
        assert exc_info.value.version == "v99"

    def test_handles_template_without_front_matter(self, tmp_prompts_dir: Path) -> None:
        """Templates without front-matter are returned as-is."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)
        content = manager.load_prompt("plain_prompt", "v1")

        assert "# Plain Prompt" in content
        assert "No metadata here." in content


class TestGetPromptVersion:
    """Tests for PromptManager.get_prompt_version()."""

    def test_extracts_version_from_front_matter(self, tmp_prompts_dir: Path) -> None:
        """Version is correctly extracted from YAML front-matter."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)
        version = manager.get_prompt_version("test_prompt", "v1")

        assert version == "v1"

    def test_extracts_v2_version(self, tmp_prompts_dir: Path) -> None:
        """Different version identifiers are extracted correctly."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)
        version = manager.get_prompt_version("test_prompt", "v2")

        assert version == "v2"

    def test_returns_unknown_without_front_matter(self, tmp_prompts_dir: Path) -> None:
        """Returns 'unknown' when template has no front-matter."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)
        version = manager.get_prompt_version("plain_prompt", "v1")

        assert version == "unknown"

    def test_raises_on_missing_template(self, tmp_prompts_dir: Path) -> None:
        """PromptNotFoundError raised for non-existent templates."""
        manager = PromptManager(prompts_dir=tmp_prompts_dir)

        with pytest.raises(PromptNotFoundError):
            manager.get_prompt_version("nonexistent", "v1")

    def test_system_prompt_has_v1_version(self, prompt_manager: PromptManager) -> None:
        """The shipped system_prompt_v1.md has version 'v1'."""
        version = prompt_manager.get_prompt_version("system_prompt", "v1")

        assert version == "v1"
