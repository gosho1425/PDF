"""pytest configuration and shared fixtures."""
from __future__ import annotations

import os

import pytest

# Set test environment variables before importing anything
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("DATA_DIR", "/tmp/paperlens_test")
os.environ.setdefault("LOG_FORMAT", "console")
os.environ.setdefault("DEBUG", "true")
