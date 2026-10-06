import { describe, expect, it } from "vitest";

import { loadedSkillInstructions, loadedSkillSummary } from "./skill-result";

// What the backend sends: `str()` of the tool result, a Python dict repr.
const PY_REPR = "{'instructions': '# Skill: greeting\\n\\nGreet the user by name.\\n\\nThen ask how they are.'}";

describe("loadedSkillInstructions", () => {
  it("reads the Python repr the chat receives", () => {
    expect(loadedSkillInstructions(PY_REPR)).toBe(
      "# Skill: greeting\n\nGreet the user by name.\n\nThen ask how they are.",
    );
  });

  it("reads JSON too", () => {
    expect(loadedSkillInstructions(JSON.stringify({ instructions: "# Skill: x\n\nDo it." }))).toBe(
      "# Skill: x\n\nDo it.",
    );
  });

  it("keeps escaped quotes as quotes", () => {
    expect(loadedSkillInstructions("{'instructions': 'Say \\'hi\\''}")).toBe("Say 'hi'");
  });

  it("is null for anything else", () => {
    expect(loadedSkillInstructions("<skill><name>x</name></skill>")).toBeNull();
  });
});

describe("loadedSkillSummary", () => {
  it("is the first paragraph after the heading", () => {
    expect(loadedSkillSummary(PY_REPR)).toBe("Greet the user by name.");
  });

  it("is null when there is nothing but the heading", () => {
    expect(loadedSkillSummary("{'instructions': '# Skill: empty'}")).toBeNull();
  });
});
