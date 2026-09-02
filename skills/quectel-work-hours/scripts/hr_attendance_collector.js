#!/usr/bin/env node
/**
 * Collect Quectel HR personal attendance clock logs from the calendar UI.
 *
 * Requires playwright-core in Node's module resolution path. Install it in a
 * temporary working directory when needed:
 *   npm install playwright-core
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { createRequire } = require('module');

const PORTAL_URL = 'https://hr.quectel.com/portal/index';
const DEFAULT_PROFILE = path.join(os.homedir(), '.cache/quectel-hr-playwright');
const WEEKDAY_X = [100, 145, 191, 236, 282, 327, 373];
const WEEK_ROW_Y = [204, 245, 285, 325, 365, 405];
const PREV_MONTH_X = 94;
const NEXT_MONTH_X = 378;
const MONTH_NAV_Y = 122;

function usage() {
  console.log(`Usage:
  node scripts/hr_attendance_collector.js --year 2026 --month 8 --out-dir /tmp/hr-2026-08

Options:
  --year YYYY              Attendance year. Defaults to current local year.
  --month M                Attendance month 1-12. Defaults to current local month.
  --out-dir DIR            Output directory. Defaults to /tmp/quectel-hr-attendance-YYYY-MM.
  --profile DIR            Persistent Chrome profile. Defaults to ~/.cache/quectel-hr-playwright.
  --chrome PATH            Chrome/Chromium executable. Auto-detected by default.
  --headless               Force headless browser.
  --headed                 Force visible browser.
  --login-timeout SECONDS  Wait time for manual SSO login. Defaults to 600.
  --credentials-stdin      Read {"username":"...","password":"..."} from stdin and fill SSO once.

Outputs:
  attendance_raw.txt       Daily blocks separated by ===== YYYY-MM-DD =====.
  attendance_rows.txt      One row per day for overtime_calculator.py.
`);
}

function parseArgs(argv) {
  const now = new Date();
  const args = {
    year: now.getFullYear(),
    month: now.getMonth() + 1,
    outDir: null,
    profile: DEFAULT_PROFILE,
    chrome: null,
    headless: process.env.DISPLAY ? false : true,
    loginTimeoutSeconds: 600,
    credentialsStdin: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--help' || arg === '-h') {
      usage();
      process.exit(0);
    } else if (arg === '--year') {
      args.year = Number(argv[++index]);
    } else if (arg === '--month') {
      args.month = Number(argv[++index]);
    } else if (arg === '--out-dir') {
      args.outDir = argv[++index];
    } else if (arg === '--profile') {
      args.profile = argv[++index];
    } else if (arg === '--chrome') {
      args.chrome = argv[++index];
    } else if (arg === '--headless') {
      args.headless = true;
    } else if (arg === '--headed') {
      args.headless = false;
    } else if (arg === '--login-timeout') {
      args.loginTimeoutSeconds = Number(argv[++index]);
    } else if (arg === '--credentials-stdin') {
      args.credentialsStdin = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!Number.isInteger(args.year) || args.year < 2000) throw new Error('Invalid --year');
  if (!Number.isInteger(args.month) || args.month < 1 || args.month > 12) throw new Error('Invalid --month');
  if (!Number.isFinite(args.loginTimeoutSeconds) || args.loginTimeoutSeconds < 1) {
    throw new Error('Invalid --login-timeout');
  }
  if (!args.outDir) {
    args.outDir = `/tmp/quectel-hr-attendance-${args.year}-${String(args.month).padStart(2, '0')}`;
  }
  return args;
}

function loadChromium() {
  const attempts = [
    () => require('playwright-core'),
    () => createRequire(path.join(process.cwd(), 'noop.js'))('playwright-core'),
  ];
  for (const attempt of attempts) {
    try {
      return attempt().chromium;
    } catch (error) {
      // Try the next module resolution base.
    }
  }
  console.error('Missing dependency: playwright-core');
  console.error('Install in a temp directory, then run this script from there: npm install playwright-core');
  process.exit(2);
}

function commandPath(command) {
  const result = spawnSync('bash', ['-lc', `command -v ${command}`], { encoding: 'utf8' });
  return result.status === 0 ? result.stdout.trim() : '';
}

function findChrome(explicitPath) {
  if (explicitPath) return explicitPath;
  for (const candidate of [
    'google-chrome',
    'google-chrome-stable',
    'chromium',
    'chromium-browser',
  ]) {
    const found = commandPath(candidate);
    if (found) return found;
  }
  for (const candidate of [
    '/home/quectel/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
  ]) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error('Chrome/Chromium executable not found. Pass --chrome PATH.');
}

function readStdinJson() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => {
      data += chunk;
    });
    process.stdin.on('end', () => {
      try {
        resolve(JSON.parse(data));
      } catch (error) {
        reject(error);
      }
    });
  });
}

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

function dayPosition(year, month, day) {
  const firstWeekday = new Date(year, month - 1, 1).getDay();
  const offset = firstWeekday + day - 1;
  return {
    x: WEEKDAY_X[offset % 7],
    y: WEEK_ROW_Y[Math.floor(offset / 7)],
  };
}

function monthHeader(text) {
  const match = text.match(/(20\d{2})年\s*(\d{1,2})月/);
  return match ? { year: Number(match[1]), month: Number(match[2]) } : null;
}

function monthDelta(current, targetYear, targetMonth) {
  return (targetYear - current.year) * 12 + (targetMonth - current.month);
}

function selectedDayBlock(text, year, month, day) {
  const normalized = text.replace(/\r/g, '');
  const monthDay = `${month}月${day}日`;
  const marker = new RegExp(`星期[^\\n]*\\/\\s*${monthDay}[\\s\\S]*?(?=\\n本月考勤信息|$)`);
  const match = normalized.match(marker);
  return match ? match[0].trim() : normalized.slice(-2000).trim();
}

function rowFromBlock(dayIso, block) {
  const clockPattern = new RegExp(`${dayIso}\\s+\\d{2}:\\d{2}(?::\\d{2})?`, 'g');
  const clocks = block.match(clockPattern) || [];
  return clocks.length ? [dayIso, ...clocks].join(' ') : dayIso;
}

async function bodyText(page) {
  return page.locator('body').innerText({ timeout: 10000 });
}

async function isSsoPage(page) {
  const url = page.url();
  if (url.includes('sso-web.quectel.com')) return true;
  const text = await bodyText(page).catch(() => '');
  return text.includes('Quectel SSO Portal') || text.includes('Log In');
}

async function fillCredentialsIfRequested(page, credentialsPromise) {
  if (!credentialsPromise) return false;
  const credentials = await credentialsPromise;
  if (!credentials || !credentials.username || !credentials.password) {
    throw new Error('credentials-stdin requires {"username":"...","password":"..."}');
  }
  await page.locator('input[placeholder="Please Enter Username"]').fill(credentials.username);
  await page.locator('input[placeholder="Please Enter Password"]').fill(credentials.password);
  await page.locator('button:has-text("Log In")').click();
  return true;
}

async function waitForLogin(page, args, credentialsPromise) {
  if (!(await isSsoPage(page))) return;

  if (args.credentialsStdin) {
    await fillCredentialsIfRequested(page, credentialsPromise);
  } else if (args.headless) {
    throw new Error('SSO login required, but browser is headless. Re-run with --headed or reuse a logged-in profile.');
  } else {
    console.error('SSO login required. Complete login in the visible browser window.');
  }

  const deadline = Date.now() + args.loginTimeoutSeconds * 1000;
  while (Date.now() < deadline) {
    await page.waitForTimeout(3000);
    if (!(await isSsoPage(page)) && page.url().includes('hr.quectel.com')) return;
  }
  throw new Error('Timed out waiting for HR SSO login.');
}

async function openAttendance(page) {
  await page.goto(PORTAL_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  let text = await bodyText(page).catch(() => '');
  if (text.includes('个人考勤查询')) {
    await page.getByText('个人考勤查询', { exact: true }).first().click({ timeout: 15000 });
  } else {
    await page.goto('https://hr.quectel.com/app/app!G8_TRwtFegd0QeO2BfN6kg', {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
  }
  await page.waitForTimeout(5000);
}

async function navigateToMonth(page, year, month) {
  for (let attempts = 0; attempts < 24; attempts += 1) {
    const text = await bodyText(page);
    const current = monthHeader(text);
    if (!current) throw new Error('Could not read attendance calendar month header.');
    const delta = monthDelta(current, year, month);
    if (delta === 0) return;
    const x = delta > 0 ? NEXT_MONTH_X : PREV_MONTH_X;
    await page.mouse.click(x, MONTH_NAV_Y);
    await page.waitForTimeout(1000);
  }
  throw new Error(`Could not navigate to ${year}-${String(month).padStart(2, '0')}`);
}

async function collectMonth(page, year, month) {
  const rawBlocks = [];
  const rows = [];
  const count = daysInMonth(year, month);

  for (let day = 1; day <= count; day += 1) {
    const { x, y } = dayPosition(year, month, day);
    const dayIso = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    await page.mouse.click(x, y);
    await page.waitForTimeout(900);
    const text = await bodyText(page);
    const block = selectedDayBlock(text, year, month, day);
    rawBlocks.push(`===== ${dayIso} =====\n${block}`);
    rows.push(rowFromBlock(dayIso, block));
    console.error(`Collected ${dayIso}`);
  }

  return {
    raw: rawBlocks.join('\n\n') + '\n',
    rows: rows.join('\n') + '\n',
  };
}

(async () => {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    usage();
    process.exit(2);
  }

  const chromium = loadChromium();
  const credentialsPromise = args.credentialsStdin ? readStdinJson() : null;
  const executablePath = findChrome(args.chrome);
  fs.mkdirSync(args.outDir, { recursive: true });

  const context = await chromium.launchPersistentContext(args.profile, {
    executablePath,
    headless: args.headless,
    viewport: { width: 1400, height: 900 },
    ignoreHTTPSErrors: true,
  });

  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(PORTAL_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await waitForLogin(page, args, credentialsPromise);
    await openAttendance(page);
    await navigateToMonth(page, args.year, args.month);
    const collected = await collectMonth(page, args.year, args.month);

    const rawPath = path.join(args.outDir, 'attendance_raw.txt');
    const rowsPath = path.join(args.outDir, 'attendance_rows.txt');
    fs.writeFileSync(rawPath, collected.raw, 'utf8');
    fs.writeFileSync(rowsPath, collected.rows, 'utf8');
    await page.screenshot({ path: path.join(args.outDir, 'attendance_final.png'), fullPage: true }).catch(() => {});

    console.log(`raw=${rawPath}`);
    console.log(`rows=${rowsPath}`);
  } finally {
    await context.close();
  }
})().catch(error => {
  console.error(error.stack || error.message);
  process.exit(1);
});
