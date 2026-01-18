# built-in imports
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import platform

class Profile:
    """Represents a configuration profile."""

    def __init__(self, name: str, description: str, path: str, last_used: Optional[str] = None):
        self.name = name
        self.description = description
        self.path = path
        self.last_used = last_used or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, str]:
        """Convert profile to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "last_used": self.last_used
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Profile':
        """Create profile from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            path=data["path"],
            last_used=data.get("last_used")
        )

class ProfileManager:
    """Manages configuration profiles."""

    def __init__(self, profiles_file: Optional[Path] = None):
        """Initialize profile manager with profiles file path."""
        if profiles_file is None:
            profiles_file = self._get_default_profiles_path()

        self.profiles_file = profiles_file
        self._ensure_directory()

    def _get_default_profiles_path(self) -> Path:
        """Get platform-specific default profiles path."""
        system = platform.system()

        if system == "Windows":
            base = Path.home() / "AppData" / "Roaming"
        elif system == "Darwin":  # macOS
            base = Path.home() / ".config"
        else:  # Linux and others
            base = Path.home() / ".config"

        return base / "basil" / "profiles.json"

    def _ensure_directory(self) -> None:
        """Ensure the profiles directory exists."""
        self.profiles_file.parent.mkdir(parents=True, exist_ok=True)

        # Also ensure configs directory exists
        configs_dir = self.profiles_file.parent / "configs"
        configs_dir.mkdir(exist_ok=True)

    def _load_profiles_data(self) -> Dict[str, Any]:
        """Load profiles data from file."""
        if not self.profiles_file.exists():
            return {"profiles": []}

        try:
            with open(self.profiles_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"profiles": []}

    def _save_profiles_data(self, data: Dict[str, Any]) -> None:
        """Save profiles data to file."""
        with open(self.profiles_file, 'w') as f:
            json.dump(data, f, indent=2)

    def list_profiles(self) -> List[Profile]:
        """Get all profiles."""
        data = self._load_profiles_data()
        return [Profile.from_dict(p) for p in data.get("profiles", [])]

    def get_profile(self, name: str) -> Optional[Profile]:
        """Get a specific profile by name."""
        profiles = self.list_profiles()
        for profile in profiles:
            if profile.name == name:
                return profile
        return None

    def profile_exists(self, name: str) -> bool:
        """Check if a profile exists."""
        return self.get_profile(name) is not None

    def add_profile(self, profile: Profile) -> None:
        """Add a new profile."""
        data = self._load_profiles_data()
        profiles = data.get("profiles", [])

        # Check for duplicate names
        if any(p["name"] == profile.name for p in profiles):
            raise ValueError(f"Profile '{profile.name}' already exists")

        profiles.append(profile.to_dict())
        data["profiles"] = profiles
        self._save_profiles_data(data)

    def update_profile(self, profile: Profile) -> None:
        """Update an existing profile."""
        data = self._load_profiles_data()
        profiles = data.get("profiles", [])

        for i, p in enumerate(profiles):
            if p["name"] == profile.name:
                profiles[i] = profile.to_dict()
                data["profiles"] = profiles
                self._save_profiles_data(data)
                return

        raise ValueError(f"Profile '{profile.name}' not found")

    def delete_profile(self, name: str, delete_file: bool = False) -> None:
        """Delete a profile and optionally its config file."""
        data = self._load_profiles_data()
        profiles = data.get("profiles", [])

        profile_to_delete = None
        new_profiles = []

        for p in profiles:
            if p["name"] == name:
                profile_to_delete = p
            else:
                new_profiles.append(p)

        if profile_to_delete is None:
            raise ValueError(f"Profile '{name}' not found")

        # Delete the encrypted config file if requested
        if delete_file:
            config_path = Path(profile_to_delete["path"]).expanduser()
            if config_path.exists():
                config_path.unlink()

        data["profiles"] = new_profiles
        self._save_profiles_data(data)

    def update_last_used(self, name: str) -> None:
        """Update the last used timestamp for a profile."""
        profile = self.get_profile(name)
        if profile is None:
            raise ValueError(f"Profile '{name}' not found")

        profile.last_used = datetime.now().isoformat()
        self.update_profile(profile)

    def get_config_path(self, profile_name: str) -> Path:
        """Get the path for a profile's config file."""
        # Sanitize profile name for use in filename
        safe_name = "".join(c for c in profile_name if c.isalnum() or c in ('-', '_')).lower()
        configs_dir = self.profiles_file.parent / "configs"
        return configs_dir / f"{safe_name}.enc"
