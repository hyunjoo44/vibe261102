// 상태를 받아 DOM을 그린다. 사용자 입력은 textContent로만 삽입한다.
const Render = (() => {
  const PRIORITY_LABEL = { high: '높음', medium: '보통', low: '낮음' };
  const $ = (id) => document.getElementById(id);

  function el(tag, props = {}) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key.startsWith('aria-') || key.startsWith('data-')) node.setAttribute(key, value);
      else node[key] = value;
    }
    return node;
  }

  function header(dateLabel) {
    $('today').textContent = dateLabel;
  }

  function progress(done, total) {
    const percent = total ? Math.round((done / total) * 100) : 0;
    $('progress-bar').style.width = `${percent}%`;
    $('progress-track').setAttribute('aria-valuenow', String(percent));
    $('progress-text').textContent = total ? `${done} / ${total} 완료 (${percent}%)` : '아직 할일이 없어요';
    $('celebrate').hidden = !(total > 0 && done === total);
  }

  function filters(active) {
    document.querySelectorAll('[data-filter]').forEach((button) => {
      const isActive = button.dataset.filter === active;
      button.classList.toggle('is-active', isActive);
      button.setAttribute('aria-selected', String(isActive));
    });
  }

  function todoItem(todo, locked) {
    const li = el('li', { class: `todo${todo.completed ? ' is-done' : ''}`, tabIndex: locked ? -1 : 0, 'data-id': todo.id });
    li.append(
      el('input', {
        type: 'checkbox',
        checked: todo.completed,
        disabled: locked,
        'aria-label': `${todo.text} 완료`,
        'data-action': 'toggle',
      }),
      el('button', {
        type: 'button',
        class: `dot dot--${todo.priority}`,
        disabled: locked,
        title: `우선순위 ${PRIORITY_LABEL[todo.priority]} (클릭해서 변경)`,
        'aria-label': `우선순위 ${PRIORITY_LABEL[todo.priority]}, 변경`,
        'data-action': 'priority',
      }),
      el('span', { class: 'todo__text', text: todo.text }),
      el('button', { type: 'button', class: 'icon-btn', disabled: locked, text: '✎', 'aria-label': `${todo.text} 수정`, 'data-action': 'edit' }),
      el('button', { type: 'button', class: 'icon-btn', disabled: locked, text: '✕', 'aria-label': `${todo.text} 삭제`, 'data-action': 'delete' }),
    );
    return li;
  }

  function editItem(todo, draft) {
    const li = el('li', { class: 'todo is-editing', 'data-id': todo.id });
    li.append(
      el('span', { class: `dot dot--${todo.priority}`, 'aria-hidden': 'true' }),
      el('input', {
        type: 'text',
        class: 'todo__edit',
        value: draft,
        maxLength: Store.MAX_LENGTH,
        'aria-label': '할일 수정 (Enter 저장, Esc 취소)',
      }),
    );
    return li;
  }

  function list(todos, { editingId, editDraft, emptyMessage }) {
    $('todo-list').replaceChildren(
      ...todos.map((todo) => (todo.id === editingId ? editItem(todo, editDraft) : todoItem(todo, Boolean(editingId)))),
    );
    $('empty').hidden = todos.length > 0;
    $('empty-text').textContent = emptyMessage;
  }

  function footer(remaining, completed) {
    $('remaining').textContent = `남은 할일 ${remaining}개`;
    $('clear-completed').disabled = completed === 0;
  }

  function carryBanner(count) {
    $('carry-banner').hidden = count === 0;
    $('carry-text').textContent = `지난번에 못 끝낸 할일 ${count}개가 있어요.`;
  }

  function storageWarning(show) {
    $('storage-warning').hidden = !show;
  }

  return { header, progress, filters, list, footer, carryBanner, storageWarning };
})();
