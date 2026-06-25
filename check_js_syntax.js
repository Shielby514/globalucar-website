const fs = require('fs');
const content = fs.readFileSync('blog-post.html', 'utf8');

// Extract BLOG_POSTS array
const startIdx = content.indexOf('const BLOG_POSTS = [');
if (startIdx < 0) { console.log('BLOG_POSTS not found'); process.exit(1); }

// Find the closing ];
let depth = 0;
let inString = false;
let strChar = '';
let escapeNext = false;
let endIdx = -1;

for (let i = startIdx + 'const BLOG_POSTS = ['.length; i < content.length; i++) {
  if (escapeNext) { escapeNext = false; continue; }
  const ch = content[i];
  if (ch === '\\') { escapeNext = true; continue; }
  if (inString) {
    if (ch === strChar) { inString = false; }
    continue;
  }
  if (ch === '\'' || ch === '"') { inString = true; strChar = ch; continue; }
  // Don't count brackets inside template literals
  if (ch === '`') {
    // Skip template literal
    let j = i + 1;
    let tEscape = false;
    for (; j < content.length; j++) {
      if (tEscape) { tEscape = false; continue; }
      if (content[j] === '\\') { tEscape = true; continue; }
      if (content[j] === '`') break;
      // Skip ${...} 
      if (content[j] === '$' && content[j+1] === '{') {
        let d = 1;
        j += 2;
        for (; j < content.length; j++) {
          if (content[j] === '{') d++;
          if (content[j] === '}') { d--; if (d === 0) break; }
        }
      }
    }
    i = j;
    continue;
  }
  if (ch === '[' || ch === '{') { depth++; continue; }
  if (ch === ']' || ch === '}') {
    depth--;
    if (depth === 0 && ch === ']') { endIdx = i; break; }
  }
}

if (endIdx < 0) {
  console.log('Could not find end of BLOG_POSTS array');
  process.exit(1);
}

const jsCode = content.substring(startIdx, endIdx + 1);
console.log('Extracted BLOG_POSTS length:', jsCode.length);

try {
  // Try to parse by wrapping in a function
  new Function(jsCode + '; return BLOG_POSTS;');
  console.log('JS syntax OK!');
} catch(e) {
  console.log('JS Syntax Error:', e.message);
  // Find the line number in the snippet
  const lines = jsCode.split('\n');
  // Try to find the problematic area
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('id: 18') && i < lines.length - 1) {
      // Check the next 100 lines for obvious issues
      for (let j = i; j < Math.min(i + 120, lines.length); j++) {
        if (lines[j].includes('${') && !lines[j].includes('\\${')) {
          console.log(`Possible unescaped \${ at approx line ${j+1}:`, lines[j].substring(0, 100));
        }
      }
      break;
    }
  }
}
