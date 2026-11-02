// 상태 관리 + localStorage 입출력
const Store = (() => {
  const KEYS = {
    todos: 'todolist:v1:todos',
    lastOpenedDate: 'todolist:v1:lastOpenedDate',
    filter: 'todolist:v1:filter',
    backup: 'todolist:v1:backup',
  };
  const MAX_LENGTH = 100;
  const PRIORITIES = ['high', 'medium', 'low'];
  const FILTERS = ['all', 'active', 'completed'];

  let storageAvailable = checkStorage();
  let state = { todos: [], filter: 'all', lastOpenedDate: null };
  const listeners = new Set();

  function checkStorage() {
    try {
      const key = 'todolist:v1:__test';
      localStorage.setItem(key, '1');
      localStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  }

  function read(key) {
    if (!storageAvailable) return null;
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function write(key, value) {
    if (!storageAvailable) return;
    try {
      localStorage.setItem(key, value);
    } catch {
      // 용량 초과 등: 이후로는 메모리로만 동작
      storageAvailable = false;
    }
  }

  function normalizeTodo(todo) {
    if (!todo || typeof todo.id !== 'string' || typeof todo.text !== 'string' || typeof todo.date !== 'string') {
      return null;
    }
    return {
      id: todo.id,
      text: todo.text.slice(0, MAX_LENGTH),
      completed: Boolean(todo.completed),
      priority: PRIORITIES.includes(todo.priority) ? todo.priority : 'medium',
      date: todo.date,
      createdAt: Number(todo.createdAt) || 0,
      completedAt: todo.completedAt ?? null,
      order: Number(todo.order) || 0,
    };
  }

  function loadTodos() {
    const raw = read(KEYS.todos);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) throw new Error('todos is not an array');
      return parsed.map(normalizeTodo).filter(Boolean);
    } catch {
      // 손상된 데이터는 백업해 두고 빈 목록으로 시작
      write(KEYS.backup, raw);
      write(KEYS.todos, '[]');
      return [];
    }
  }

  function load() {
    const filter = read(KEYS.filter);
    state = {
      todos: loadTodos(),
      filter: FILTERS.includes(filter) ? filter : 'all',
      lastOpenedDate: read(KEYS.lastOpenedDate),
    };
  }

  function persist() {
    write(KEYS.todos, JSON.stringify(state.todos));
    write(KEYS.filter, state.filter);
    if (state.lastOpenedDate) write(KEYS.lastOpenedDate, state.lastOpenedDate);
  }

  function notify() {
    listeners.forEach((listener) => listener(state));
  }

  function commit(nextState) {
    state = { ...state, ...nextState };
    persist();
    notify();
  }

  function mapTodo(id, fn) {
    return state.todos.map((todo) => (todo.id === id ? fn(todo) : todo));
  }

  function getState() {
    return state;
  }

  function isStorageAvailable() {
    return storageAvailable;
  }

  function addTodo(text, priority = 'medium') {
    const clean = text.trim().slice(0, MAX_LENGTH);
    if (!clean) return null;
    const todo = {
      id: Utils.createId(),
      text: clean,
      completed: false,
      priority: PRIORITIES.includes(priority) ? priority : 'medium',
      date: Utils.toDateKey(),
      createdAt: Date.now(),
      completedAt: null,
      order: state.todos.reduce((max, t) => Math.max(max, t.order), 0) + 1,
    };
    commit({ todos: [...state.todos, todo] });
    return todo;
  }

  function toggleTodo(id) {
    commit({
      todos: mapTodo(id, (todo) => ({
        ...todo,
        completed: !todo.completed,
        completedAt: todo.completed ? null : Date.now(),
      })),
    });
  }

  function updateTodo(id, patch) {
    const changes = {};
    if (typeof patch.text === 'string') {
      const clean = patch.text.trim().slice(0, MAX_LENGTH);
      if (clean) changes.text = clean;
    }
    if (PRIORITIES.includes(patch.priority)) changes.priority = patch.priority;
    commit({ todos: mapTodo(id, (todo) => ({ ...todo, ...changes })) });
  }

  function cyclePriority(id) {
    const todo = state.todos.find((t) => t.id === id);
    if (!todo) return;
    const next = PRIORITIES[(PRIORITIES.indexOf(todo.priority) + 1) % PRIORITIES.length];
    updateTodo(id, { priority: next });
  }

  function deleteTodo(id) {
    const removed = state.todos.find((todo) => todo.id === id);
    if (!removed) return null;
    commit({ todos: state.todos.filter((todo) => todo.id !== id) });
    return removed;
  }

  function restoreTodo(todo) {
    if (state.todos.some((t) => t.id === todo.id)) return;
    commit({ todos: [...state.todos, todo] });
  }

  function clearCompleted(date) {
    commit({ todos: state.todos.filter((todo) => !(todo.completed && todo.date === date)) });
  }

  function setFilter(filter) {
    if (!FILTERS.includes(filter)) return;
    commit({ filter });
  }

  // 마지막 사용일에 끝내지 못한 할일 (오늘 처음 열었을 때만)
  function getCarryOverCandidates(today) {
    const last = state.lastOpenedDate;
    if (!last || last === today) return [];
    return state.todos.filter((todo) => !todo.completed && todo.date === last);
  }

  function carryOver(today) {
    const ids = new Set(getCarryOverCandidates(today).map((todo) => todo.id));
    commit({
      todos: state.todos.map((todo) => (ids.has(todo.id) ? { ...todo, date: today } : todo)),
      lastOpenedDate: today,
    });
  }

  function markOpened(today) {
    if (state.lastOpenedDate === today) return;
    commit({ lastOpenedDate: today });
  }

  function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  // 다른 탭에서 변경된 내용 반영
  window.addEventListener('storage', (event) => {
    if (event.key && !event.key.startsWith('todolist:v1:')) return;
    load();
    notify();
  });

  return {
    MAX_LENGTH,
    load,
    getState,
    isStorageAvailable,
    addTodo,
    toggleTodo,
    updateTodo,
    cyclePriority,
    deleteTodo,
    restoreTodo,
    clearCompleted,
    setFilter,
    getCarryOverCandidates,
    carryOver,
    markOpened,
    subscribe,
  };
})();
