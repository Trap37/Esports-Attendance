// node --test tests/frontend.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const here = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(here, '..');
const source = fs.readFileSync(path.join(projectRoot, 'static', 'app.js'), 'utf8');

function createHarness() {
  const handlers = new Map();
  const elements = new Map();
  const document = {
    addEventListener: (name, callback) => {
      const values = handlers.get(name) ?? [];
      values.push(callback);
      handlers.set(name, values);
    },
    getElementById: (id) => elements.get(id) ?? null,
    querySelectorAll: (selector) => selector === '.modal-overlay'
      ? [...elements.values()].filter((element) => element.isModal)
      : [],
  };

  function element(id, hidden = false, isModal = false) {
    const classes = new Set(hidden ? ['hidden'] : []);
    const item = {
      id,
      isModal,
      focused: false,
      classList: {
        add: (name) => classes.add(name),
        remove: (name) => classes.delete(name),
        contains: (name) => classes.has(name),
      },
      focus() { this.focused = true; },
    };
    elements.set(id, item);
    return item;
  }

  element('scan-input');
  element('modal-register', true, true);
  element('modal-checkout', true, true);
  element('modal-return', true, true);
  element('modal-edit', true, true);
  const context = vm.createContext({
    document,
    window: {},
    console,
    setInterval: () => 0,
    fetch: async () => { throw new Error('Unexpected fetch in isolated frontend unit test'); },
    alert: () => {},
  });
  vm.runInContext(source, context, { filename: 'app.js' });
  return { context, document, elements, handlers };
}

test('escapeHtml escapes all HTML-sensitive characters', () => {
  const { context } = createHarness();
  assert.equal(context.escapeHtml(`<&>"'`), '&lt;&amp;&gt;&quot;&#39;');
});

test('escapeHtml converts nullish and numeric inputs to strings safely', () => {
  const { context } = createHarness();
  assert.equal(context.escapeHtml(123), '123');
  assert.equal(context.escapeHtml(null), 'null');
  assert.equal(context.escapeHtml(undefined), 'undefined');
});

test('opening a modal removes hidden state', () => {
  const { context, elements } = createHarness();
  context.openModal('modal-register');
  assert.equal(elements.get('modal-register').classList.contains('hidden'), false);
});

test('closing the last modal hides it and restores scan input focus', () => {
  const { context, elements } = createHarness();
  context.openModal('modal-register');
  context.closeModal('modal-register');
  assert.equal(elements.get('modal-register').classList.contains('hidden'), true);
  assert.equal(elements.get('scan-input').focused, true);
});

test('closing one modal does not focus scan input while another modal remains open', () => {
  const { context, elements } = createHarness();
  context.openModal('modal-register');
  context.openModal('modal-checkout');
  context.closeModal('modal-register');
  assert.equal(elements.get('scan-input').focused, false);
  assert.equal(elements.get('modal-checkout').classList.contains('hidden'), false);
});

test('Escape closes all modal overlays and focuses the scan field', () => {
  const { context, elements, handlers } = createHarness();
  context.openModal('modal-register');
  context.openModal('modal-edit');
  const keydownHandlers = handlers.get('keydown') ?? [];
  assert.equal(keydownHandlers.length, 1);
  keydownHandlers[0]({ key: 'Escape' });
  assert.equal(elements.get('modal-register').classList.contains('hidden'), true);
  assert.equal(elements.get('modal-edit').classList.contains('hidden'), true);
  assert.equal(elements.get('scan-input').focused, true);
});

// The full DOM workflows are integration-tested separately by the Flask test
// client and template/JavaScript contract tests in test_frontend_contract.py.
