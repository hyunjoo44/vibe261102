// 진입점: 이벤트 바인딩과 화면 갱신
(() => {
  const $ = (id) => document.getElementById(id);
  const form = $('todo-form');
  const input = $('new-todo');
  const counter = $('char-count');
  const list = $('todo-list');
  const toast = $('toast');

  const PRIORITY_RANK = { high: 0, medium: 1, low: 2 };
  const FILTER_FN = {
    all: () => true,
    active: (todo) => !todo.completed,
    completed: (todo) => todo.completed,
  };
  const EMPTY_MESSAGE = {
    all: '오늘 할 일을 추가해 보세요',
    active: '진행 중인 할일이 없어요',
    completed: '아직 완료한 할일이 없어요',
  };
  const TOAST_DURATION = 5000;

  let today = Utils.toDateKey();
  let editingId = null;
  let editDraft = '';
  let carryCount = 0;
  let toastTimer = null;
  let undoAction = null;

  // 미완료 우선 → 우선순위 높은 순 → 생성 순
  function sortTodos(todos) {
    return [...todos].sort(
      (a, b) =>
        Number(a.completed) - Number(b.completed) ||
        PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority] ||
        a.createdAt - b.createdAt,
    );
  }

  function render() {
    const state = Store.getState();
    const todays = sortTodos(state.todos.filter((todo) => todo.date === today));
    const done = todays.filter((todo) => todo.completed).length;

    if (editingId && !todays.some((todo) => todo.id === editingId)) editingId = null;

    Render.header(Utils.formatKoreanDate());
    Render.progress(done, todays.length);
    Render.filters(state.filter);
    Render.list(todays.filter(FILTER_FN[state.filter]), { editingId, editDraft, emptyMessage: EMPTY_MESSAGE[state.filter] });
    Render.footer(todays.length - done, done);
    Render.carryBanner(carryCount);
    Render.storageWarning(!Store.isStorageAvailable());

    if (editingId) {
      const editor = list.querySelector('.todo__edit');
      if (editor && document.activeElement !== editor) {
        editor.focus();
        editor.setSelectionRange(editor.value.length, editor.value.length);
      }
    }
  }

  function checkDate() {
    today = Utils.toDateKey();
    carryCount = Store.getCarryOverCandidates(today).length;
    if (carryCount === 0) Store.markOpened(today);
  }

  function focusItem(id) {
    const item = list.querySelector(`[data-id="${CSS.escape(id)}"]`);
    if (item) item.focus();
  }

  function shake(element) {
    element.classList.remove('shake');
    void element.offsetWidth; // 애니메이션 재시작
    element.classList.add('shake');
  }

  function updateCounter() {
    counter.textContent = `${input.value.length} / ${Store.MAX_LENGTH}`;
  }

  function selectedPriority() {
    return form.querySelector('input[name="priority"]:checked')?.value ?? 'medium';
  }

  function showToast(message, onUndo) {
    clearTimeout(toastTimer);
    $('toast-text').textContent = message;
    undoAction = onUndo;
    toast.hidden = false;
    toastTimer = setTimeout(hideToast, TOAST_DURATION);
  }

  function hideToast() {
    clearTimeout(toastTimer);
    toast.hidden = true;
    undoAction = null;
  }

  function deleteWithUndo(id) {
    const removed = Store.deleteTodo(id);
    if (removed) showToast('삭제됨', () => Store.restoreTodo(removed));
  }

  function startEdit(id) {
    if (editingId === id) return;
    if (editingId) commitEdit();
    const todo = Store.getState().todos.find((t) => t.id === id);
    if (!todo) return;
    editingId = id;
    editDraft = todo.text;
    render();
  }

  function commitEdit() {
    if (!editingId) return;
    const id = editingId;
    editingId = null;
    if (!editDraft.trim()) {
      if (confirm('내용이 비어 있습니다. 이 할일을 삭제할까요?')) {
        deleteWithUndo(id);
        return;
      }
      render();
      focusItem(id);
      return;
    }
    Store.updateTodo(id, { text: editDraft });
    focusItem(id);
  }

  function cancelEdit() {
    if (!editingId) return;
    const id = editingId;
    editingId = null;
    render();
    focusItem(id);
  }

  function isTyping(target) {
    return target.matches('input[type="text"], textarea, [contenteditable="true"]');
  }

  // --- 이벤트 ---

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!Store.addTodo(input.value, selectedPriority())) {
      shake(input);
      return;
    }
    input.value = '';
    updateCounter();
    if (Store.getState().filter === 'completed') Store.setFilter('all');
  });

  input.addEventListener('input', updateCounter);

  list.addEventListener('change', (event) => {
    const item = event.target.closest('[data-id]');
    if (item && event.target.dataset.action === 'toggle') Store.toggleTodo(item.dataset.id);
  });

  list.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    const item = event.target.closest('[data-id]');
    if (!button || !item) return;
    const { id } = item.dataset;
    if (button.dataset.action === 'edit') startEdit(id);
    else if (button.dataset.action === 'delete') deleteWithUndo(id);
    else if (button.dataset.action === 'priority') Store.cyclePriority(id);
  });

  list.addEventListener('dblclick', (event) => {
    const item = event.target.closest('[data-id]');
    if (item && event.target.classList.contains('todo__text')) startEdit(item.dataset.id);
  });

  list.addEventListener('input', (event) => {
    if (event.target.classList.contains('todo__edit')) editDraft = event.target.value;
  });

  list.addEventListener('keydown', (event) => {
    if (event.target.classList.contains('todo__edit')) {
      if (event.key === 'Enter') {
        event.preventDefault();
        commitEdit();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        cancelEdit();
      }
      return;
    }
    const item = event.target.closest('[data-id]');
    if (item && event.key === 'Delete') {
      event.preventDefault();
      const next = item.nextElementSibling || item.previousElementSibling;
      deleteWithUndo(item.dataset.id);
      if (next) focusItem(next.dataset.id);
    }
  });

  list.addEventListener('focusout', (event) => {
    if (event.target.classList.contains('todo__edit')) commitEdit();
  });

  document.querySelectorAll('[data-filter]').forEach((button) => {
    button.addEventListener('click', () => Store.setFilter(button.dataset.filter));
  });

  $('clear-completed').addEventListener('click', () => {
    const count = Store.getState().todos.filter((todo) => todo.completed && todo.date === today).length;
    if (count && confirm(`완료한 할일 ${count}개를 지울까요?`)) Store.clearCompleted(today);
  });

  $('carry-accept').addEventListener('click', () => {
    carryCount = 0;
    Store.carryOver(today);
  });

  $('carry-discard').addEventListener('click', () => {
    carryCount = 0;
    Store.markOpened(today);
  });

  $('toast-undo').addEventListener('click', () => {
    const action = undoAction;
    hideToast();
    if (action) action();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !isTyping(event.target)) {
      event.preventDefault();
      input.focus();
    }
  });

  // 자정이 지난 채로 열려 있는 경우
  function onWake() {
    if (Utils.toDateKey() === today) return;
    checkDate();
    render();
  }
  window.addEventListener('focus', onWake);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) onWake();
  });
  setInterval(onWake, 60 * 1000);

  // --- 시작 ---
  Store.load();
  Store.subscribe(render);
  checkDate();
  render();
  updateCounter();
})();
