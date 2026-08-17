#!/usr/bin/env node
/**
 * Copy public/ directory contents to build/ root
 * Removes the incorrectly-created build/public/ directory
 */

const fs = require('fs');
const path = require('path');

function copyDir(src, dest) {
  if (!fs.existsSync(src)) return;

  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const files = fs.readdirSync(src);
  files.forEach(file => {
    const srcPath = path.join(src, file);
    const destPath = path.join(dest, file);
    const stat = fs.statSync(srcPath);

    if (stat.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  });
}

function rmDir(dirPath) {
  if (!fs.existsSync(dirPath)) return;

  const files = fs.readdirSync(dirPath);
  files.forEach(file => {
    const filePath = path.join(dirPath, file);
    const stat = fs.statSync(filePath);

    if (stat.isDirectory()) {
      rmDir(filePath);
    } else {
      fs.unlinkSync(filePath);
    }
  });

  fs.rmdirSync(dirPath);
}

const projectRoot = path.resolve(__dirname, '..');
const publicDir = path.join(projectRoot, 'public');
const buildDir = path.join(projectRoot, 'build');
const buildPublicDir = path.join(buildDir, 'public');

// Copy public/ contents to build/
copyDir(publicDir, buildDir);

// Remove the duplicate build/public/ directory
if (fs.existsSync(buildPublicDir)) {
  rmDir(buildPublicDir);
}

console.log('✓ Public files copied to build root');
