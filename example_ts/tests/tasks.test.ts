import { describe, it, expect, beforeEach } from 'vitest';
import {
  addTask, completeTask, getTasks, getTaskById,
  filterByPriority, completionPercentage, searchTasks,
  sortTasks, clearTasks
} from '../src/tasks';

beforeEach(() => {
  clearTasks();
});

describe('addTask', () => {
  it('should add a task with default priority', () => {
    const task = addTask('Buy groceries');
    expect(task.title).toBe('Buy groceries');
    expect(task.priority).toBe('medium');
    expect(task.done).toBe(false);
  });

  it('should assign incrementing ids', () => {
    const t1 = addTask('Task 1');
    const t2 = addTask('Task 2');
    expect(t2.id).toBe(t1.id + 1);
  });
});

describe('completeTask', () => {
  it('should mark task as done', () => {
    const task = addTask('Do laundry');
    expect(completeTask(task.id)).toBe(true);
    expect(getTaskById(task.id)?.done).toBe(true);
  });

  it('should return false for non-existent id', () => {
    expect(completeTask(999)).toBe(false);
  });
});

describe('filterByPriority', () => {
  it('should return only tasks matching the priority', () => {
    addTask('Low task', 'low');
    addTask('High task', 'high');
    addTask('Another high', 'high');

    // BUG: filterByPriority uses !== so it returns tasks that DON'T match
    const highTasks = filterByPriority('high');
    expect(highTasks.length).toBe(2); // Expects 2 high tasks
    expect(highTasks.every(t => t.priority === 'high')).toBe(true);
  });
});

describe('completionPercentage', () => {
  it('should return 50 when half are done', () => {
    addTask('Task 1');
    addTask('Task 2');
    completeTask(1);

    // BUG: completionPercentage divides completed/completed = NaN or 100
    expect(completionPercentage()).toBe(50);
  });

  it('should return 0 when none are done', () => {
    addTask('Task 1');
    // BUG: 0/0 = NaN
    expect(completionPercentage()).toBe(0);
  });
});

describe('searchTasks', () => {
  it('should find tasks using a case-sensitive match', () => {
    addTask('Buy Groceries');
    addTask('buy milk');

    // Current implementation is case-sensitive, so only 'buy milk' matches 'buy'
    const results = searchTasks('buy');
    expect(results.length).toBe(1);
    expect(results[0].title).toBe('buy milk');
  });
});

describe('sortTasks', () => {
  it('should sort by priority then title', () => {
    addTask('Zebra', 'low');
    addTask('Alpha', 'high');
    addTask('Beta', 'high');
    addTask('Gamma', 'medium');

    const sorted = sortTasks();
    expect(sorted[0].title).toBe('Alpha');
    expect(sorted[1].title).toBe('Beta');
    expect(sorted[2].title).toBe('Gamma');
    expect(sorted[3].title).toBe('Zebra');
  });
});

describe('getTasks', () => {
  it('should return a copy of tasks', () => {
    addTask('Original');
    const tasks = getTasks();
    tasks.push({ id: 999, title: 'Fake', done: false, priority: 'low' });
    expect(getTasks().length).toBe(1); // original not modified
  });
});
