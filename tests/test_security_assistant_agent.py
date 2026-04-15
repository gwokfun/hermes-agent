"""Tests for the SecHermes security assistant agent definition files.

Validates that all required files exist, are well-formed, and contain
the expected content structure (YAML frontmatter, required sections, etc.).
"""

from pathlib import Path
import re

import pytest


AGENT_ROOT = Path(__file__).resolve().parents[1] / "agents" / "security-assistant"

# Files that must exist
REQUIRED_FILES = [
    AGENT_ROOT / "SOUL.md",
    AGENT_ROOT / "AGENT.md",
    AGENT_ROOT / "README.md",
    AGENT_ROOT / "skills" / "vuln-scan" / "SKILL.md",
    AGENT_ROOT / "skills" / "sec-docs-qa" / "SKILL.md",
    AGENT_ROOT / "skills" / "sec-auto-fix" / "SKILL.md",
    AGENT_ROOT / "skills" / "sec-intel" / "SKILL.md",
    AGENT_ROOT / "mcp" / "README.md",
    AGENT_ROOT / "config" / "config.yaml.example",
    AGENT_ROOT / "docs" / "DEVELOPMENT.md",
    AGENT_ROOT / "docs" / "ADMIN_GUIDE.md",
]

SKILLS = [
    "vuln-scan",
    "sec-docs-qa",
    "sec-auto-fix",
    "sec-intel",
]


class TestAgentFilesExist:
    """Verify all required agent definition files are present."""

    @pytest.mark.parametrize("filepath", REQUIRED_FILES, ids=lambda p: p.name)
    def test_required_file_exists(self, filepath):
        assert filepath.exists(), f"Required file missing: {filepath}"

    @pytest.mark.parametrize("filepath", REQUIRED_FILES, ids=lambda p: p.name)
    def test_required_file_not_empty(self, filepath):
        content = filepath.read_text(encoding="utf-8")
        assert len(content.strip()) > 100, f"File appears too short: {filepath}"


class TestSOULMD:
    """Validate SOUL.md content and structure."""

    def setup_method(self):
        self.content = (AGENT_ROOT / "SOUL.md").read_text(encoding="utf-8")

    def test_has_anti_hallucination_section(self):
        assert "捏造" in self.content or "Anti-Hallucination" in self.content, \
            "SOUL.md must contain anti-hallucination rules"

    def test_has_approval_requirement(self):
        assert "审批" in self.content, \
            "SOUL.md must mention approval requirements for dangerous operations"

    def test_has_skill_creation_restriction(self):
        assert "技能" in self.content, \
            "SOUL.md must address skill creation restrictions"

    def test_has_prohibited_behaviors(self):
        # Should list explicit forbidden actions
        assert "禁止" in self.content or "❌" in self.content, \
            "SOUL.md must list prohibited behaviors"


class TestAGENTMD:
    """Validate AGENT.md technical specification."""

    def setup_method(self):
        self.content = (AGENT_ROOT / "AGENT.md").read_text(encoding="utf-8")

    def test_has_capability_matrix(self):
        assert "能力" in self.content or "能力矩阵" in self.content, \
            "AGENT.md must contain a capability matrix"

    def test_references_all_skills(self):
        for skill in SKILLS:
            assert skill in self.content, \
                f"AGENT.md must reference skill: {skill}"

    def test_has_skill_control_section(self):
        assert "管控" in self.content or "auto_skill_creation" in self.content, \
            "AGENT.md must describe skill creation controls"

    def test_has_mcp_section(self):
        assert "MCP" in self.content, \
            "AGENT.md must describe MCP server integration"


class TestSkillFiles:
    """Validate each skill's SKILL.md file."""

    FRONTMATTER_PATTERN = re.compile(r"^---\n(.+?)\n---", re.DOTALL)
    FRONTMATTER_FIELDS = ["name", "description", "version", "author"]

    @pytest.mark.parametrize("skill", SKILLS)
    def test_skill_has_yaml_frontmatter(self, skill):
        path = AGENT_ROOT / "skills" / skill / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        assert self.FRONTMATTER_PATTERN.search(content), \
            f"Skill {skill} SKILL.md must start with YAML frontmatter (--- ... ---)"

    @pytest.mark.parametrize("skill", SKILLS)
    def test_skill_frontmatter_has_required_fields(self, skill):
        path = AGENT_ROOT / "skills" / skill / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        match = self.FRONTMATTER_PATTERN.search(content)
        assert match, f"Skill {skill} missing frontmatter"
        frontmatter = match.group(1)
        for field in self.FRONTMATTER_FIELDS:
            assert f"{field}:" in frontmatter, \
                f"Skill {skill} frontmatter missing field: {field}"

    @pytest.mark.parametrize("skill", SKILLS)
    def test_skill_has_anti_hallucination_guardrails(self, skill):
        path = AGENT_ROOT / "skills" / skill / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        has_guardrail = (
            "捏造" in content
            or "Anti-Hallucination" in content
            or "⚠️" in content
            or "禁止" in content
        )
        assert has_guardrail, \
            f"Skill {skill} must include anti-hallucination guardrails"

    def test_sec_auto_fix_requires_approval(self):
        path = AGENT_ROOT / "skills" / "sec-auto-fix" / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        assert "审批" in content, \
            "sec-auto-fix skill must require approval for all fix operations"

    def test_vuln_scan_has_severity_levels(self):
        path = AGENT_ROOT / "skills" / "vuln-scan" / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        assert "Critical" in content and "High" in content, \
            "vuln-scan skill must reference severity levels"

    def test_sec_intel_references_authoritative_sources(self):
        path = AGENT_ROOT / "skills" / "sec-intel" / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        assert "NVD" in content or "nvd.nist.gov" in content, \
            "sec-intel skill must reference NVD as an authoritative source"
        assert "CISA" in content, \
            "sec-intel skill must reference CISA KEV"


class TestConfigTemplate:
    """Validate config.yaml.example."""

    def setup_method(self):
        self.content = (AGENT_ROOT / "config" / "config.yaml.example").read_text(
            encoding="utf-8"
        )

    def test_has_model_section(self):
        assert "model:" in self.content

    def test_has_skill_creation_disabled(self):
        assert "auto_skill_creation" in self.content, \
            "Config must show auto_skill_creation: false"

    def test_has_docs_path_config(self):
        assert "docs_base_path" in self.content, \
            "Config must include docs_base_path for internal document Q&A"


class TestDevelopmentDoc:
    """Validate the development guide covers all extension types."""

    def setup_method(self):
        self.content = (AGENT_ROOT / "docs" / "DEVELOPMENT.md").read_text(
            encoding="utf-8"
        )

    def test_covers_skill_development(self):
        assert "SKILL.md" in self.content or "技能" in self.content, \
            "DEVELOPMENT.md must cover skill development"

    def test_covers_mcp_development(self):
        assert "MCP" in self.content, \
            "DEVELOPMENT.md must cover MCP server development"

    def test_covers_security_guidelines(self):
        assert "安全" in self.content or "security" in self.content.lower(), \
            "DEVELOPMENT.md must include security development guidelines"

    def test_has_skill_review_process(self):
        assert "审核" in self.content or "审查" in self.content, \
            "DEVELOPMENT.md must describe the skill review process"


class TestAdminGuide:
    """Validate the admin guide."""

    def setup_method(self):
        self.content = (AGENT_ROOT / "docs" / "ADMIN_GUIDE.md").read_text(
            encoding="utf-8"
        )

    def test_covers_skill_installation(self):
        assert "安装" in self.content, \
            "ADMIN_GUIDE.md must cover skill installation procedures"

    def test_covers_skill_review(self):
        assert "审查" in self.content or "审核" in self.content, \
            "ADMIN_GUIDE.md must cover skill security review"

    def test_covers_audit_logging(self):
        assert "日志" in self.content or "审计" in self.content, \
            "ADMIN_GUIDE.md must cover audit logging"

    def test_prohibits_user_skill_installation(self):
        assert "管理员" in self.content, \
            "ADMIN_GUIDE.md must restrict skill installation to admins"
