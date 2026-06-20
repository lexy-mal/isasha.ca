#!/usr/bin/env node
/**
 * Injects Google Analytics into all HTML files in the public directory
 * Run: node scripts/inject-ga.js
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

const GA_SCRIPT = `    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-9SV5JFP7RJ"><\/script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-9SV5JFP7RJ');
    <\/script>`;

function injectGA(filePath) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');

    // Check if GA is already injected
    if (content.includes('G-9SV5JFP7RJ')) {
      console.log(`✓ ${filePath} - GA already present`);
      return false;
    }

    // Check if it's an HTML file with <head>
    if (!content.includes('<head>')) {
      console.log(`✗ ${filePath} - No <head> tag found, skipping`);
      return false;
    }

    // Inject after <head> tag
    const headEndPattern = /<head>/i;
    content = content.replace(headEndPattern, `<head>\n${GA_SCRIPT}\n`);

    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`✓ ${filePath} - GA injected`);
    return true;
  } catch (error) {
    console.error(`✗ ${filePath} - Error: ${error.message}`);
    return false;
  }
}

function main() {
  const projectRoot = path.resolve(__dirname, '..');

  // Find all HTML files in public directory and subdirectories
  const htmlFiles = glob.sync(path.join(projectRoot, 'public/**/*.html'), {
    ignore: '**/node_modules/**'
  });

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
