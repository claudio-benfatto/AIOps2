// Enforced by the commitlint hook in .pre-commit-config.yaml (commit-msg
// stage). Scopes mirror the module map in
// .claude/skills/git-workflow/SKILL.md — keep the two in sync.
//
// CommonJS on purpose: there's no package.json ("type": "module") at the
// repo root, and `npx commitlint` needs to load this without one.
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "scope-enum": [
      2,
      "always",
      [
        "llm-sim",
        "agent-svc",
        "search-api",
        "retrieval-svc",
        "common",
        "go/load-gen",
        "investigator",
        "go/injector",
        "lab",
        "scenarios",
        "deploy",
        "topology",
        "docs",
        "repo",
      ],
    ],
    "scope-empty": [0],
  },
};
