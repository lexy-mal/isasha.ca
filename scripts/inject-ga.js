#!/usr/bin/env node
/**
 * Injects Google Analytics into all HTML files in the public directory
 * Run: node scripts/inject-ga.js
 * Uses only Node built-in modules (no external dependencies)
 */

const fs = require('fs');
const path = require('path');

const GA_SCRIPT = `    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-9SV5JFP7RJ"><\/script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-9SV5JFP7RJ');
    <\/script>`;

function findHtmlFiles(dir, fileList = []) {
  try {
    const files = fs.readdirSync(dir);

    files.forEach(file => {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);

      if (stat.isDirectory()) {
        // Skip node_modules and hidden directories
        if (!file.startsWith('.') && file !== 'node_modules') {
          findHtmlFiles(filePath, fileList);
        }
      } else if (file.endsWith('.html')) {
        fileList.push(filePath);
      }
    });
  } catch (error) {
    console.error(`Error reading directory ${dir}: ${error.message}`);
  }

  return fileList;
}

function injectGA(filePath) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');

    // Check if GA is already injected
    if (content.includes('G-9SV5JFP7RJ')) {
      console.log(`✓ ${path.relative(process.cwd(), filePath)} - GA already present`);
      return false;
    }

    // Check if it's an HTML file with <head>
    if (!content.includes('<head>')) {
      console.log(`✗ ${path.relative(process.cwd(), filePath)} - No <head> tag found, skipping`);
      return false;
    }

    // Inject after <head> tag
    const headEndPattern = /<head>/i;
    content = content.replace(headEndPattern, `<head>\n${GA_SCRIPT}\n`);

    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`✓ ${path.relative(process.cwd(), filePath)} - GA injected`);
    return true;
  } catch (error) {
    console.error(`✗ ${filePath} - Error: ${error.message}`);
    return false;
  }
}

function main() {
  const projectRoot = path.resolve(__dirname, '..');
  const publicDir = path.join(projectRoot, 'public');

  // Check if public directory exists
  if (!fs.existsSync(publicDir)) {
    console.log('Public directory not found, skipping GA injection for static files');
    return;
  }

  // Find all HTML files in public directory and subdirectories
  const htmlFiles = findHtmlFiles(publicDir);

  if (htmlFiles.length === 0) {
    console.log('No HTML files found in public directory');
    return;
  }

  console.log(`Found ${htmlFiles.length} HTML file(s)\n`);

  let injected = 0;
  htmlFiles.forEach(file => {
    if (injectGA(file)) {
      injected++;
    }
  });

  console.log(`\n✓ Complete! Injected GA into ${injected} file(s)`);
}

main();
