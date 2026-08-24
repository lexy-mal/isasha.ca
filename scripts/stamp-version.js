#!/usr/bin/env node
/**
 * Write public/projects/com_assets/version.json from git metadata.
 * Build number = total commits on HEAD (increases with each pushed commit).
 * Run before deploy/build so the footer shows the current release.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function git(cmd) {
  return execSync(cmd, { encoding: 'utf8', cwd: path.resolve(__dirname, '..') }).trim();
}

let build;
let commit;
try {
  build = parseInt(git('git rev-list --count HEAD'), 10);
  commit = git('git rev-parse --short HEAD');
} catch (e) {
  console.warn('stamp-version: git unavailable, using fallback', e.message);
  build = 0;
  commit = 'local';
}

const version = {
  build,
  commit,
  updatedAt: new Date().toISOString(),
};

const outPath = path.join(__dirname, '../public/projects/com_assets/version.json');
fs.writeFileSync(outPath, JSON.stringify(version, null, 2) + '\n');
console.log(`✓ Stamped version.json → build ${build} (${commit})`);
