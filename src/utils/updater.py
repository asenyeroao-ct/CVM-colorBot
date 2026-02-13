"""
Update Checker Module
Handles version checking and update notifications
"""
from src.utils.debug_logger import log_print
import json
import os
import sys
import requests
from packaging import version as pkg_version

# Repository URLs
GITHUB_REPO = "https://raw.githubusercontent.com/asenyeroao-ct/CVM-colorBot/main"
GITEE_REPO = "https://gitee.com/asenyeroao-ct/CVM-colorBot/raw/main"

# Timeout for requests (seconds)
REQUEST_TIMEOUT = 5

class UpdateChecker:
    """Handles version checking and update management"""
    
    def __init__(self):
        self.current_version = None
        self.latest_version = None
        self.latest_info = None
        self.update_skipped_version = None
        self.never_update = False
        
        # Load current version
        self._load_current_version()
        
        # Load update preferences from config
        self._load_update_preferences()
    
    def _load_current_version(self):
        """Load current version from version.json"""
        try:
            version_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "version.json")
            if os.path.exists(version_path):
                with open(version_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_version = data.get("version", "1.0.0")
            else:
                self.current_version = "1.0.0"
        except Exception as e:
            log_print(f"[Updater] Failed to load current version: {e}")
            self.current_version = "1.0.0"
    
    def _load_update_preferences(self):
        """Load update preferences from config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.update_skipped_version = config.get("update_skipped_version", None)
                    self.never_update = config.get("never_update", False)
        except Exception as e:
            log_print(f"[Updater] Failed to load update preferences: {e}")
    
    def _save_update_preferences(self):
        """Save update preferences to config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config["update_skipped_version"] = self.update_skipped_version
            config["never_update"] = self.never_update
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            log_print(f"[Updater] Failed to save update preferences: {e}")
    
    def check_update(self, use_gitee=False):
        """
        Check for updates from GitHub or Gitee
        
        Args:
            use_gitee: If True, use Gitee as primary source, otherwise use GitHub
            
        Returns:
            tuple: (has_update: bool, latest_version: str, update_info: dict)
        """
        if self.never_update:
            return False, None, None
        
        # Try to fetch from primary source first
        primary_repo = GITEE_REPO if use_gitee else GITHUB_REPO
        fallback_repo = GITHUB_REPO if use_gitee else GITEE_REPO
        
        # Try primary source
        update_info = self._fetch_version_info(primary_repo)
        
        # If primary fails, try fallback
        if not update_info:
            log_print(f"[Updater] Primary source failed, trying fallback...")
            update_info = self._fetch_version_info(fallback_repo)
        
        if not update_info:
            return False, None, None
        
        self.latest_version = update_info.get("version", "1.0.0")
        self.latest_info = update_info
        
        # Check if update is available
        try:
            current = pkg_version.parse(self.current_version)
            latest = pkg_version.parse(self.latest_version)
            
            if latest > current:
                # Check if this version was skipped
                if self.update_skipped_version == self.latest_version:
                    return False, self.latest_version, update_info
                return True, self.latest_version, update_info
            else:
                return False, self.latest_version, update_info
        except Exception as e:
            log_print(f"[Updater] Version comparison error: {e}")
            return False, None, None
    
    def _fetch_version_info(self, repo_url):
        """
        Fetch version information from repository
        
        Args:
            repo_url: Base URL of the repository
            
        Returns:
            dict: Version information or None if failed
        """
        try:
            version_url = f"{repo_url}/version.json"
            response = requests.get(version_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log_print(f"[Updater] Failed to fetch version from {repo_url}: {e}")
            return None
        except json.JSONDecodeError as e:
            log_print(f"[Updater] Failed to parse version JSON: {e}")
            return None
    
    def skip_update(self):
        """Mark current update as skipped"""
        if self.latest_version:
            self.update_skipped_version = self.latest_version
            self._save_update_preferences()
    
    def set_never_update(self, value=True):
        """Set never update preference"""
        self.never_update = value
        self._save_update_preferences()
    
    def get_current_version(self):
        """Get current version string"""
        return self.current_version
    
    def get_latest_version(self):
        """Get latest version string"""
        return self.latest_version
    
    def get_update_info(self):
        """Get latest update information"""
        return self.latest_info


def get_update_checker():
    """Get singleton instance of UpdateChecker"""
    if not hasattr(get_update_checker, '_instance'):
        get_update_checker._instance = UpdateChecker()
    return get_update_checker._instance
