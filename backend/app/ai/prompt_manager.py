"""
Prompt Manager — loads versioned prompt templates from files.

Prompts are stored as markdown files in the `prompts/` directory, separate
from service, repository, and API modules. Each template includes a YAML
front-matter block with version and name metadata.

Usage:
    manager = PromptManager()
    prompt = manager.load_prompt("system_prompt", version="v1")
    version = manager.get_prompt_version("system_prompt")
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Directory containing prompt template files, relative to this module
_PROMPTS_DIR = Path(__file__).parent / "prompts"

# Front-matter delimiter used in markdown templates
_FRONT_MATTER_DELIMITER = "---"


class PromptNotFoundError(Exception):
    """Raised when a requested prompt template file does not exist."""

    def __init__(self, name: str, version: str, path: Path) -> None:
        self.name = name
        self.version = version
        self.path = path
        super().__init__(
            f"Prompt template not found: name='{name}', version='{version}', "
            f"expected at '{path}'"
        )


class PromptManager:
    """Loads and manages versioned prompt templates from the prompts directory.

    Templates are markdown files with YAML front-matter containing metadata
    (version, name). The file naming convention is: `{name}_{version}.md`.

    Example:
        system_prompt_v1.md  →  name="system_prompt", version="v1"
    """

    def __init__(self, prompts_dir: Path | None = None) -> None:
        """Initialize the prompt manager.

        Args:
            prompts_dir: Override directory for prompt templates.
                Defaults to the `prompts/` subdirectory next to this module.
        """
        self._prompts_dir = prompts_dir or _PROMPTS_DIR

    def load_prompt(self, name: str, version: str = "v1") -> str:
        """Load a prompt template by name and version.

        Reads the markdown file, strips YAML front-matter, and returns
        the template body content.

        Args:
            name: The prompt template name (e.g., "system_prompt").
            version: The version identifier (e.g., "v1"). Defaults to "v1".

        Returns:
            The prompt template content (without front-matter).

        Raises:
            PromptNotFoundError: If the template file does not exist.
        """
        file_path = self._resolve_path(name, version)

        if not file_path.exists():
            raise PromptNotFoundError(name=name, version=version, path=file_path)

        raw_content = file_path.read_text(encoding="utf-8")
        body = self._strip_front_matter(raw_content)

        logger.debug(
            "prompt_loaded",
            extra={"prompt_name": name, "prompt_version": version, "path": str(file_path)},
        )

        return body

    def get_prompt_version(self, name: str, version: str = "v1") -> str:
        """Extract the version identifier from a prompt template's front-matter.

        Args:
            name: The prompt template name (e.g., "system_prompt").
            version: The file version to read (e.g., "v1"). Defaults to "v1".

        Returns:
            The version string from the template's front-matter metadata.

        Raises:
            PromptNotFoundError: If the template file does not exist.
        """
        file_path = self._resolve_path(name, version)

        if not file_path.exists():
            raise PromptNotFoundError(name=name, version=version, path=file_path)

        raw_content = file_path.read_text(encoding="utf-8")
        return self._extract_version(raw_content)

    def _resolve_path(self, name: str, version: str) -> Path:
        """Build the file path for a prompt template.

        Convention: {prompts_dir}/{name}_{version}.md
        """
        filename = f"{name}_{version}.md"
        return self._prompts_dir / filename

    def _strip_front_matter(self, content: str) -> str:
        """Remove YAML front-matter from template content.

        Front-matter is delimited by `---` on its own line at the start
        and end of the metadata block.

        Returns:
            The content body without front-matter, stripped of leading whitespace.
        """
        lines = content.split("\n")

        if not lines or lines[0].strip() != _FRONT_MATTER_DELIMITER:
            return content

        # Find the closing delimiter
        end_index = None
        for i in range(1, len(lines)):
            if lines[i].strip() == _FRONT_MATTER_DELIMITER:
                end_index = i
                break

        if end_index is None:
            # No closing delimiter found — return content as-is
            return content

        body = "\n".join(lines[end_index + 1 :])
        return body.lstrip("\n")

    def _extract_version(self, content: str) -> str:
        """Extract the version value from YAML front-matter.

        Parses the front-matter block looking for a `version:` key.

        Returns:
            The version string, or "unknown" if not found.
        """
        lines = content.split("\n")

        if not lines or lines[0].strip() != _FRONT_MATTER_DELIMITER:
            return "unknown"

        for i in range(1, len(lines)):
            line = lines[i].strip()
            if line == _FRONT_MATTER_DELIMITER:
                break
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip()

        return "unknown"
