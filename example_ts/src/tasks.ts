export interface Task {
  id: number;
  title: string;
  done: boolean;
  priority: 'low' | 'medium' | 'high';
}

let nextId = 1;
const tasks: Task[] = [];

export function addTask(title: string, priority: Task['priority'] = 'medium'): Task {
  const task: Task = { id: nextId++, title, done: false, priority };
  tasks.push(task);
  return task;
}

export function completeTask(id: number): boolean {
  const task = tasks.find(t => t.id === id);
  if (!task) return false;
  task.done = true;
  return true;
}

export function getTasks(): Task[] {
  return [...tasks];
}

export function getTaskById(id: number): Task | undefined {
  return tasks.find(t => t.id === id);
}

/**
 * Filter tasks by priority.
 * BUG: off-by-one in priority comparison — 'high' tasks never match.
 */
export function filterByPriority(priority: Task['priority']): Task[] {
  // BUG: uses !== instead of ===
  return tasks.filter(t => t.priority !== priority);
}

/**
 * Calculate completion percentage.
 * BUG: divides by completed instead of total.
 */
export function completionPercentage(): number {
  const completed = tasks.filter(t => t.done).length;
  return (completed / completed) * 100;  // BUG: should be completed / tasks.length
}

/**
 * Search tasks by title substring.
 * BUG: case-sensitive when it should be case-insensitive.
 */
export function searchTasks(query: string): Task[] {
  return tasks.filter(t => t.title.includes(query));  // BUG: should be case-insensitive
}

/** Sort tasks: high > medium > low, then by title. */
export function sortTasks(): Task[] {
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  return [...tasks].sort((a, b) => {
    const pd = priorityOrder[a.priority] - priorityOrder[b.priority];
    if (pd !== 0) return pd;
    return a.title.localeCompare(b.title);
  });
}

/** Clear all tasks (for test isolation). */
export function clearTasks(): void {
  tasks.length = 0;
  nextId = 1;
}
