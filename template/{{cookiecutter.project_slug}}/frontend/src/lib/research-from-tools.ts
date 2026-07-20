import { RESEARCH_TOOL_NAMES } from "@/components/chat/research-panel";
import type { ResearchReplay, ResearchTodo, SubagentStatus, ToolCall } from "@/types";

// Re-exported from the canonical set in research-panel.tsx (which mirrors the
// backend `RESEARCH_TOOL_NAMES`) so the tool-name list lives in one place.
export { RESEARCH_TOOL_NAMES };

const ADD_TODO = "add_todo";
const ADD_SUBTASK = "add_subtask";
const WRITE_TODOS = "write_todos";
const TASK = "task";

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function reconstructResearch(toolCalls: ToolCall[]): ResearchReplay | null {
  const todos: ResearchTodo[] = [];
  const subagents: SubagentStatus[] = [];
  let lastRootId: string | null = null;

  const pushTodo = (content: string, activeForm: string, parentId: string | null, key: string) => {
    if (!content) return;
    const id = `rt-${key}`;
    todos.push({
      id,
      content,
      status: "completed",
      active_form: activeForm || content,
      parent_id: parentId,
      depends_on: [],
    });
    if (parentId === null) lastRootId = id;
  };

  toolCalls.forEach((tc, i) => {
    const args = (tc.args ?? {}) as Record<string, unknown>;
    switch (tc.name) {
      case ADD_TODO:
        pushTodo(asString(args.content), asString(args.active_form), null, `${i}`);
        break;
      case ADD_SUBTASK:
        pushTodo(asString(args.content), asString(args.active_form), lastRootId, `${i}`);
        break;
      case WRITE_TODOS: {
        // write_todos replaces the whole list, so reset before appending —
        // otherwise a transcript that calls it more than once duplicates rows.
        todos.length = 0;
        lastRootId = null;
        const list = Array.isArray(args.todos) ? args.todos : [];
        list.forEach((entry, j) => {
          const e = (entry ?? {}) as Record<string, unknown>;
          pushTodo(asString(e.content), asString(e.active_form), null, `${i}-${j}`);
        });
        break;
      }
      case TASK:
        subagents.push({
          task_id: `rs-${i}`,
          subagent_name: asString(args.subagent_type) || "subagent",
          description: asString(args.description),
          status: "completed",
          error: null,
          result: asString(tc.result) || null,
        });
        break;
    }
  });

  if (todos.length === 0 && subagents.length === 0) return null;
  return { todos, subagents };
}
