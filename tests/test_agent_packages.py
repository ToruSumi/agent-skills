import tempfile
import unittest
from pathlib import Path

import yaml

from apm_cli.deps.apm_resolver import APMDependencyResolver
from apm_cli.integration.agent_integrator import AgentIntegrator
from apm_cli.integration.opencode_frontmatter import validate_opencode_frontmatter
from apm_cli.integration.targets import KNOWN_TARGETS
from apm_cli.models.apm_package import APMPackage
from apm_cli.models.dependency.reference import DependencyReference


ROOT = Path(__file__).resolve().parents[1]
AGENT_NAMES = {"acli", "architect", "implementer"}


def load_frontmatter(source: Path) -> dict:
    return yaml.safe_load(source.read_text(encoding="utf-8").split("---", 2)[1])


class AgentPackageTests(unittest.TestCase):
    def test_external_dependencies_are_pinned(self) -> None:
        package = APMPackage.from_apm_yml(ROOT / "apm.yml")
        remote = [dependency for dependency in package.get_apm_dependencies() if not dependency.is_local]
        self.assertEqual(len(remote), 2)
        for dependency in remote:
            with self.subTest(dependency=dependency.repo_url):
                self.assertRegex(dependency.reference or "", r"^(?:[0-9a-f]{40}|v\d+\.\d+\.\d+)$")

    def test_agent_packages_have_exclusive_targets(self) -> None:
        package = APMPackage.from_apm_yml(ROOT / "apm.yml")
        local = [dependency for dependency in package.get_apm_dependencies() if dependency.is_local]
        self.assertEqual(len(local), 2)
        for dependency in local:
            with self.subTest(package=dependency.local_path):
                source = ROOT / dependency.local_path
                child = APMPackage.from_apm_yml(source / "apm.yml")
                self.assertEqual(dependency.target_subset, [source.name])
                self.assertEqual(child.targets, dependency.target_subset)
                self.assertEqual(child.version, package.version)
                names = {agent.name.removesuffix(".agent.md") for agent in (source / ".apm/agents").glob("*.agent.md")}
                self.assertEqual(names, AGENT_NAMES)

    def test_remote_subpackages_inherit_parent_revision_and_targets(self) -> None:
        package = APMPackage.from_apm_yml(ROOT / "apm.yml")
        with tempfile.TemporaryDirectory() as temporary:
            modules = Path(temporary) / "apm_modules"
            parent = DependencyReference.parse("ToruSumi/agent-skills#" + "a" * 40)
            package.source_path = parent.get_install_path(modules)
            package.source_path.mkdir(parents=True)
            resolver = APMDependencyResolver(apm_modules_dir=modules)
            for child in package.get_apm_dependencies():
                if not child.is_local:
                    continue
                with self.subTest(package=child.local_path):
                    expanded = resolver._expand_remote_parent_local_path(parent, package, child)
                    self.assertFalse(expanded.is_local)
                    self.assertEqual(expanded.repo_url, parent.repo_url)
                    self.assertEqual(expanded.host, parent.host)
                    self.assertEqual(expanded.reference, parent.reference)
                    self.assertEqual(expanded.virtual_path, child.local_path.removeprefix("./"))
                    self.assertEqual(expanded.target_subset, child.target_subset)

    def test_root_does_not_deploy_nested_agent_packages(self) -> None:
        self.assertEqual(AgentIntegrator().find_agent_files(ROOT), [])

    def test_frontmatter_is_native_to_each_target(self) -> None:
        for target in ("copilot", "opencode"):
            for source in (ROOT / "packages" / target / ".apm/agents").glob("*.agent.md"):
                with self.subTest(target=target, agent=source.name):
                    frontmatter = load_frontmatter(source)
                    self.assertTrue(frontmatter.get("description"))
                    if target == "copilot":
                        if "tools" in frontmatter:
                            self.assertIsInstance(frontmatter["tools"], list)
                        self.assertNotIn("permissions", frontmatter)
                    else:
                        self.assertEqual(validate_opencode_frontmatter(frontmatter, source), [])
                        self.assertTrue(frontmatter["permissions"])
                        self.assertIn(frontmatter["mode"], ("all", "subagent"))
                        for field in ("tools", "model", "name", "agents", "user-invocable"):
                            self.assertNotIn(field, frontmatter)

    def test_architect_can_only_delegate_to_installed_implementer(self) -> None:
        agents = ROOT / "packages/opencode/.apm/agents"
        architect = load_frontmatter(agents / "architect.agent.md")
        implementer = agents / "implementer.agent.md"
        deployed = AgentIntegrator().get_target_filename_for_target(implementer, "agent-skills-opencode", KNOWN_TARGETS["opencode"])
        allowed = [rule["resource"] for rule in architect["permissions"] if rule["action"] == "subagent" and rule["effect"] == "allow"]
        self.assertEqual(allowed, [Path(deployed).stem])
        self.assertEqual(load_frontmatter(implementer)["mode"], "subagent")
        editable = [rule["resource"] for rule in architect["permissions"] if rule["action"] == "edit" and rule["effect"] == "allow"]
        self.assertEqual(editable, ["docs/design/**"])


if __name__ == "__main__":
    unittest.main()