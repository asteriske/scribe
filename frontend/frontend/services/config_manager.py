"""Configuration manager for tag-based summarization configs and secrets."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, NamedTuple

logger = logging.getLogger(__name__)

# Default config directory relative to the services module
DEFAULT_CONFIG_DIR = Path(__file__).parent.parent / "config"


class ResolvedConfig(NamedTuple):
    """Resolved configuration for a summarization request."""

    api_endpoint: str
    model: str
    api_key: str  # Resolved from env or secrets file
    system_prompt: str
    config_source: str  # e.g., "tag:supersummarize" or "system_default"


class ConfigManager:
    """Manages tag configurations and secrets for summarization."""

    def __init__(self, config_dir: Path = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory containing config files (defaults to frontend/config)
        """
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.tag_configs_path = self.config_dir / "tag_configs.json"
        self.secrets_path = self.config_dir / "secrets.json"

    def _ensure_config_dir(self):
        """Ensure config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _read_tag_configs(self) -> Dict[str, Any]:
        """Read tag configurations from file."""
        if not self.tag_configs_path.exists():
            return self._get_default_tag_configs()

        try:
            with open(self.tag_configs_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read tag_configs.json: {e}")
            return self._get_default_tag_configs()

    def _write_tag_configs(self, configs: Dict[str, Any]) -> bool:
        """Write tag configurations to file."""
        self._ensure_config_dir()
        try:
            with open(self.tag_configs_path, 'w', encoding='utf-8') as f:
                json.dump(configs, f, indent=2, ensure_ascii=False)
            logger.info("Tag configs saved successfully")
            return True
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to write tag_configs.json: {e}")
            return False

    def _read_secrets(self) -> Dict[str, str]:
        """Read secrets from file."""
        if not self.secrets_path.exists():
            return {}

        try:
            with open(self.secrets_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read secrets.json: {e}")
            return {}

    def _write_secrets(self, secrets: Dict[str, str]) -> bool:
        """Write secrets to file."""
        self._ensure_config_dir()
        try:
            with open(self.secrets_path, 'w', encoding='utf-8') as f:
                json.dump(secrets, f, indent=2, ensure_ascii=False)
            logger.info("Secrets saved successfully")
            return True
        except (IOError, PermissionError) as e:
            logger.error(f"Failed to write secrets.json: {e}")
            return False

    def _get_default_tag_configs(self) -> Dict[str, Any]:
        """Get default tag configuration structure."""
        return {
            "default": {
                "api_endpoint": "http://localhost:11434/v1",
                "model": "llama2",
                "api_key_ref": None,
                "system_prompt": "Provide a concise summary of the following transcription:"
            },
            "tags": {}
        }

    def resolve_api_key(self, api_key_ref: Optional[str]) -> str:
        """
        Resolve API key from environment variable or secrets file.

        Resolution order:
        1. Environment variable: {API_KEY_REF}_API_KEY (uppercase)
        2. Secrets file: secrets.json[api_key_ref]
        3. Empty string if not found

        Args:
            api_key_ref: Reference name for the API key (e.g., "openai")

        Returns:
            Resolved API key or empty string
        """
        if not api_key_ref:
            return ""

        # Try environment variable first
        env_var_name = f"{api_key_ref.upper()}_API_KEY"
        env_value = os.environ.get(env_var_name)
        if env_value:
            logger.debug(f"Using API key from environment variable: {env_var_name}")
            return env_value

        # Try secrets file
        secrets = self._read_secrets()
        if api_key_ref in secrets:
            logger.debug(f"Using API key from secrets.json: {api_key_ref}")
            return secrets[api_key_ref]

        logger.warning(f"API key not found for ref: {api_key_ref}")
        return ""

    def resolve_config_for_transcription(self, transcription_tags: List[str]) -> ResolvedConfig:
        """
        Resolve configuration based on transcription tags.

        Resolution order:
        1. Iterate through transcription tags in order
        2. If tag exists in tag_configs["tags"], use that config
        3. Fallback to default config if no tag matches

        Args:
            transcription_tags: List of tags associated with the transcription

        Returns:
            ResolvedConfig with API endpoint, model, key, and prompt
        """
        configs = self._read_tag_configs()
        tags_config = configs.get("tags", {})

        # Find first matching tag configuration
        for tag in transcription_tags:
            if tag in tags_config:
                tag_config = tags_config[tag]
                api_key = self.resolve_api_key(tag_config.get("api_key_ref"))
                return ResolvedConfig(
                    api_endpoint=tag_config["api_endpoint"],
                    model=tag_config["model"],
                    api_key=api_key,
                    system_prompt=tag_config["system_prompt"],
                    config_source=f"tag:{tag}"
                )

        # Fallback to default
        default_config = configs.get("default", self._get_default_tag_configs()["default"])
        api_key = self.resolve_api_key(default_config.get("api_key_ref"))
        return ResolvedConfig(
            api_endpoint=default_config["api_endpoint"],
            model=default_config["model"],
            api_key=api_key,
            system_prompt=default_config["system_prompt"],
            config_source="system_default"
        )

    # Tag Configuration CRUD Operations

    def get_all_tag_configs(self) -> Dict[str, Any]:
        """Get all tag configurations."""
        return self._read_tag_configs()

    def get_tag_config(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific tag."""
        configs = self._read_tag_configs()
        return configs.get("tags", {}).get(tag_name)

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        configs = self._read_tag_configs()
        return configs.get("default", self._get_default_tag_configs()["default"])

    def create_tag_config(
        self,
        tag_name: str,
        api_endpoint: str,
        model: str,
        system_prompt: str,
        api_key_ref: Optional[str] = None,
        destination_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Create a new tag configuration.

        Args:
            tag_name: Name of the tag
            api_endpoint: API endpoint URL
            model: Model name
            system_prompt: System prompt for summarization
            api_key_ref: Optional reference to API key
            destination_emails: Optional list of email addresses to send results to

        Returns:
            True if created successfully, False otherwise
        """
        configs = self._read_tag_configs()
        if "tags" not in configs:
            configs["tags"] = {}

        configs["tags"][tag_name] = {
            "api_endpoint": api_endpoint,
            "model": model,
            "api_key_ref": api_key_ref,
            "system_prompt": system_prompt,
            "destination_emails": destination_emails or []
        }

        return self._write_tag_configs(configs)

    def update_tag_config(
        self,
        tag_name: str,
        api_endpoint: str,
        model: str,
        system_prompt: str,
        api_key_ref: Optional[str] = None,
        destination_emails: Optional[List[str]] = None
    ) -> bool:
        """Update an existing tag configuration."""
        configs = self._read_tag_configs()
        if tag_name not in configs.get("tags", {}):
            logger.warning(f"Tag config not found: {tag_name}")
            return False

        configs["tags"][tag_name] = {
            "api_endpoint": api_endpoint,
            "model": model,
            "api_key_ref": api_key_ref,
            "system_prompt": system_prompt,
            "destination_emails": destination_emails or []
        }

        return self._write_tag_configs(configs)

    def delete_tag_config(self, tag_name: str) -> bool:
        """Delete a tag configuration."""
        configs = self._read_tag_configs()
        if tag_name not in configs.get("tags", {}):
            logger.warning(f"Tag config not found: {tag_name}")
            return False

        del configs["tags"][tag_name]
        return self._write_tag_configs(configs)

    def update_default_config(
        self,
        api_endpoint: str,
        model: str,
        system_prompt: str,
        api_key_ref: Optional[str] = None
    ) -> bool:
        """Update the default configuration."""
        configs = self._read_tag_configs()
        configs["default"] = {
            "api_endpoint": api_endpoint,
            "model": model,
            "api_key_ref": api_key_ref,
            "system_prompt": system_prompt
        }
        return self._write_tag_configs(configs)

    # Secrets Management

    def list_secret_names(self) -> List[str]:
        """Get list of secret key names (not values)."""
        secrets = self._read_secrets()
        return list(secrets.keys())

    def add_secret(self, key_name: str, key_value: str) -> bool:
        """Add or update a secret."""
        secrets = self._read_secrets()
        secrets[key_name] = key_value
        return self._write_secrets(secrets)

    def delete_secret(self, key_name: str) -> bool:
        """Delete a secret."""
        secrets = self._read_secrets()
        if key_name not in secrets:
            logger.warning(f"Secret not found: {key_name}")
            return False

        del secrets[key_name]
        return self._write_secrets(secrets)

    def has_secret(self, key_name: str) -> bool:
        """Check if a secret exists."""
        secrets = self._read_secrets()
        return key_name in secrets
