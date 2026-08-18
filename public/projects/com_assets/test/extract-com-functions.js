'use strict';
/**
 * Loads the pure, DOM-free functions out of ../../com.html for unit testing, without
 * pulling in jsdom or executing the whole page (which does real fetches, DOM lookups,
 * and a password gate on load).
 *
 * Approach: extract named top-level declarations (function ... / const ... =) from the
 * app's inline <script> by structurally scanning the raw text, concatenate them in
 * dependency order, and run that as a classic (non-module) script via Node's vm module.
 * Top-level `function` declarations in a vm Script attach to the sandbox object, so they
 * come back out as sandbox.<name>; `const` bindings referenced *inside* those functions
 * still resolve correctly via closure even though they don't appear on the sandbox
 * themselves — we only need the functions, not direct access to the data tables, since
 * everything under test is exercised through the public function API.
 *
 * If a target symbol is renamed or removed in com.html, extraction throws immediately
 * with the symbol name, rather than silently testing stale/empty code.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const COM_HTML_PATH = path.join(__dirname, '..', '..', 'com.html');

function readAppScriptSource() {
  const html = fs.readFileSync(COM_HTML_PATH, 'utf8');
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  const appScript = scripts.find(s => s.includes('AGE_CATEGORY_MAP'));
  if (!appScript) {
    throw new Error('Could not find the app <script> block (expected one containing AGE_CATEGORY_MAP) in com.html');
  }
  return appScript;
}

const OPENERS = new Set(['{', '[', '(']);
const CLOSERS = new Set(['}', ']', ')']);

// Advances one "token" from index i, skipping line/block comments and string/template
// literals whole, and regex literals whole (heuristically: a '/' not immediately
// preceded by an identifier char, ')' or ']' is treated as opening a regex — true for
// every regex in this codebase, which only ever follow '(', ',', 'return', '=', or
// start-of-line). Returns { i: nextIndex, delta: depth change (+1/-1/0) }.
function step(source, i) {
  const ch = source[i];

  if (ch === '/' && source[i + 1] === '/') {
    const nl = source.indexOf('\n', i);
    return { i: nl === -1 ? source.length : nl + 1, delta: 0 };
  }
  if (ch === '/' && source[i + 1] === '*') {
    const end = source.indexOf('*/', i + 2);
    if (end === -1) throw new Error('Unterminated block comment');
    return { i: end + 2, delta: 0 };
  }
  if (ch === '"' || ch === "'" || ch === '`') {
    const quote = ch;
    let j = i + 1;
    while (j < source.length && source[j] !== quote) {
      if (source[j] === '\\') j++;
      j++;
    }
    return { i: j + 1, delta: 0 };
  }
  if (ch === '/' && !/[\w)\]]\s*$/.test(source.slice(Math.max(0, i - 4), i))) {
    let j = i + 1;
    let inClass = false;
    while (j < source.length) {
      if (source[j] === '\\') { j += 2; continue; }
      if (source[j] === '[') inClass = true;
      else if (source[j] === ']') inClass = false;
      else if (source[j] === '/' && !inClass) break;
      j++;
    }
    j++; // consume closing '/'
    while (j < source.length && /[a-z]/i.test(source[j])) j++; // flags
    return { i: j, delta: 0 };
  }
  if (OPENERS.has(ch)) return { i: i + 1, delta: 1 };
  if (CLOSERS.has(ch)) return { i: i + 1, delta: -1 };
  return { i: i + 1, delta: 0 };
}

// Given source[i] is an opening bracket, returns the index just past its matching closer.
function skipBalancedGroup(source, i) {
  if (!OPENERS.has(source[i])) {
    throw new Error(`skipBalancedGroup: expected an opening bracket at offset ${i}, got '${source[i]}'`);
  }
  let depth = 0;
  while (i < source.length) {
    const { i: next, delta } = step(source, i);
    depth += delta;
    i = next;
    if (depth === 0) return i;
  }
  throw new Error('Reached end of source while balancing brackets starting at offset ' + i);
}

// Scans from i (typically right after a `const X =`) to the first top-level ';' —
// i.e. depth returns to 0 — and returns the index just past it. Handles any RHS shape:
// object/array literals, `new Set([...])`, plain expressions, etc.
function scanToTopLevelSemicolon(source, i) {
  let depth = 0;
  while (i < source.length) {
    if (depth === 0 && source[i] === ';') return i + 1;
    const { i: next, delta } = step(source, i);
    depth += delta;
    i = next;
  }
  throw new Error('Reached end of source while scanning for top-level ";" starting at offset ' + i);
}

function extractDeclaration(source, name) {
  const fnMatch = source.match(new RegExp(`function\\s+${name}\\s*\\(`));
  if (fnMatch) {
    const declStart = fnMatch.index;
    const parenStart = declStart + fnMatch[0].length - 1; // index of the '(' itself
    const afterParams = skipBalancedGroup(source, parenStart);
    const braceStart = source.indexOf('{', afterParams);
    if (braceStart === -1) throw new Error(`No function body found for "${name}"`);
    const end = skipBalancedGroup(source, braceStart);
    return source.slice(declStart, end);
  }

  const constMatch = source.match(new RegExp(`const\\s+${name}\\s*=`));
  if (constMatch) {
    const declStart = constMatch.index;
    const afterEquals = declStart + constMatch[0].length;
    const end = scanToTopLevelSemicolon(source, afterEquals);
    return source.slice(declStart, end);
  }

  throw new Error(`Could not find declaration for "${name}" in com.html's app script — was it renamed or removed?`);
}

/**
 * Loads the given symbol names (function/const declarations from com.html's app script)
 * into a fresh vm context and returns the sandbox. `extraPrelude` is prepended verbatim —
 * used by tests that need to seed a `let`-declared global (e.g. `resultsData`) that
 * getPersonPlacement reads, since `let` bindings at vm top level aren't visible on the
 * sandbox object the way `function`/`var` are.
 */
function loadComFunctions(names, extraPrelude = '') {
  const source = readAppScriptSource();
  const declarations = names.map(name => extractDeclaration(source, name));
  const bundle = extraPrelude + '\n' + declarations.join('\n\n');

  const sandbox = {};
  vm.createContext(sandbox);
  try {
    vm.runInContext(bundle, sandbox, { filename: 'com.html (extracted)' });
  } catch (e) {
    throw new Error(`Extracted bundle failed to run: ${e.message}\n--- bundle ---\n${bundle}`);
  }
  return sandbox;
}

// Every symbol under test, plus their internal const dependencies, in dependency order.
// Kept in one place so test files don't need to know com.html's internal wiring — they
// just call loadAllComFunctions() and use whichever function they need.
const ALL_SYMBOLS = [
  'AGE_CATEGORY_MAP',
  'SKILL_LEVEL_CODES',
  'getEventAgeCategory',
  'SKILL_LEVELS',
  'SKILL_LEVEL_LOOKUP_ORDER',
  'getEventSkillLevel',
  'LEVEL_RANK_COLORS',
  'LEVEL_RANK_COUNT',
  'getLevelChipHtml',
  'getAgeChipHtml',
  'getEventDivision',
  'compareHeatsBySort',
  'buildAgeFilterPanelHtml',
  'formatName',
  'formatPlacement',
  'jsQuote',
  'onclickArg',
];

function loadAllComFunctions(extraPrelude = '') {
  return loadComFunctions(ALL_SYMBOLS, extraPrelude);
}

module.exports = { loadComFunctions, loadAllComFunctions, ALL_SYMBOLS, readAppScriptSource, extractDeclaration };
