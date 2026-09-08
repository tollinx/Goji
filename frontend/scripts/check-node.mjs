// Vite 6 needs Node 18+. On older Node it fails deep inside config resolution
// with "crypto$2.getRandomValues is not a function", which says nothing about
// the real cause. Fail here instead, with the fix.
const MINIMUM = 18;
const major = Number(process.versions.node.split('.')[0]);

if (major < MINIMUM) {
  console.error(
    `\n  Node ${process.versions.node} is too old — this app needs Node ${MINIMUM}+.\n\n` +
      `  Fix it in this terminal:\n` +
      `      nvm use 20\n\n` +
      `  Already-open terminals keep the Node they started with, so a new\n` +
      `  terminal window works too.\n`
  );
  process.exit(1);
}
