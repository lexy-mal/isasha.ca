#!/usr/bin/env node
/**
 * Write public/projects/com_assets/version.json from git metadata.
 * Build number = total commits on HEAD when full history is available.
 * On shallow clones (Cloudflare/Pages depth=1), increments from the last
 * stamped version.json so the footer keeps counting up.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function git(cmd) {
  return execSync(cmd, { encoding: 'utf8', cwd: path.resolve(__dirname, '..') }).trim();
}

const outPath = path.join(__dirname, '../public/projects/com_assets/version.json');

function readExistingVersion() {
  try {
    return JSON.parse(fs.readFileSync(outPath, 'utf8'));
  } catch {
    return { build: 0, commit: '' };
  }
}

const prev = readExistingVersion();
let build;
let commit;

try {
  commit = git('git rev-parse --short HEAD');
  const gitBuild = parseInt(git('git rev-list --count HEAD'), 10);

  if (gitBuild <= 1 && prev.build > 0) {
    // Shallow clone — git always reports 1 commit.
    build = prev.commit === commit ? prev.build : prev.build + 1;
  } else if (commit !== prev.commit) {
    build = Math.max(gitBuild, prev.build + 1);
  } else {
    build = Math.max(gitBuild, prev.build);
  }
} catch (e) {
  console.warn('stamp-version: git unavailable, using fallback', e.message);
  commit = prev.commit || 'local';
  build = prev.commit === commit ? prev.build : prev.build + 1;
}

const version = {
  build,
  commit,
  updatedAt: new Date().toISOString(),
};

fs.writeFileSync(outPath, JSON.stringify(version, null, 2) + '\n');
console.log(`✓ Stamped version.json → build ${build} (${commit})`);
