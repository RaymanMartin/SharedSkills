---
name: quectel-work-hours
description: Log in to Quectel HR attendance portal and summarize natural-month overtime from personal attendance records.
---

# Quectel 工时统计

Use this skill when the user asks to统计、核算、导出或复核 Quectel HR 个人考勤的自然月加班时长.

## Source

- Portal: `https://hr.quectel.com/portal/index`
- Feature: 个人考勤查询
- Scope: one natural month unless the user states a different range.
- Never ask the user to paste or store a password in a file. If login is required, open the HR portal in an interactive browser/session and let the user complete authentication.

## Workflow

1. Determine the month to report. If the user does not specify one, use the current natural month in the local timezone.
2. Open the HR portal and navigate to 个人考勤查询.
3. Query the selected natural month and capture the attendance rows. Prefer exporting the table to CSV/XLSX if the UI offers it; otherwise copy the visible table text.
4. For each attendance day, identify valid clock times of that date. Ignore rows with no valid clock time.
5. Apply the overtime rule below and produce a concise month summary plus a daily breakdown.

## HR Clock-Log Retrieval Chain

Use this retrieval flow when the user asks to recalculate from HR directly instead of providing an export:

1. Enter `https://hr.quectel.com/portal/index`.
2. If redirected to SSO, authenticate in the browser session. Do not store passwords in files. If the user explicitly gives credentials for this run, pass them only through an interactive/session stdin or browser fields, never through command-line arguments or committed scripts.
3. After login, confirm the HR home page shows the user's profile and application menu.
4. Open the attendance feature by clicking `个人考勤查询`. The observed app route may be a relative link like `app/app!G8_TRwtFegd0QeO2BfN6kg`; rediscover it from the home page if it changes.
5. Confirm the attendance modal title is `个人考勤查询` and the calendar header is the requested month, such as `2026年8月`. Use the month arrows only if the selected month is different.
6. For each day in the requested natural month, click that date on the calendar and read the right-side `当日打卡记录` section.
7. Save raw daily blocks with a clear delimiter before each day:

```text
===== 2026-08-30 =====
星期日 / 8月30日 正常
...
当日打卡记录
2026-08-30 10:21:41
2026-08-30 17:19:51
```

8. Convert raw daily blocks into one attendance row per date before running overtime calculation. This matters because the calculator expects all clock times for a date on the same row.

```bash
python3 scripts/hr_daily_blocks_to_rows.py august_raw.txt august_rows.txt
python3 scripts/overtime_calculator.py august_rows.txt
```

For an end-to-end browser collection, use `scripts/hr_attendance_collector.js`. It opens HR, handles SSO state, enters `个人考勤查询`, clicks each day in the month, and writes both raw daily blocks and calculator rows.

```bash
node scripts/hr_attendance_collector.js --year 2026 --month 8 --out-dir /tmp/quectel-hr-2026-08
python3 scripts/overtime_calculator.py /tmp/quectel-hr-2026-08/attendance_rows.txt
```

### Browser Automation Notes

- The browser collector requires `playwright-core` in Node's module resolution path. If it is not installed, install it in a temporary working directory and run the script from there:

```bash
npm install playwright-core
node /home/quectel/.shared-skills/skills/quectel-work-hours/scripts/hr_attendance_collector.js --year 2026 --month 8
```

- Prefer reusing an existing persistent browser profile if one is present. On this workstation, the default collector profile is `/home/quectel/.cache/quectel-hr-playwright`.
- The collector auto-detects Chrome from `google-chrome`, `google-chrome-stable`, `chromium`, or `chromium-browser`. Use `--chrome PATH` if auto-detection fails.
- If a visible browser cannot start because `$DISPLAY` or XServer is unavailable, use headless mode only when there is already a valid login session or the user has explicitly allowed credential entry for that run.
- If credentials are explicitly supplied for the current run, do not put the password in CLI arguments. Use `--credentials-stdin` and pass JSON through stdin only for that one run:

```bash
node scripts/hr_attendance_collector.js --year 2026 --month 8 --credentials-stdin
```

- HR can display the home page in Chinese even after an English login page. Search/click `个人考勤查询`, not only `My Attendance`.
- The attendance page is calendar-driven. If there is no export button, click each date and collect `当日打卡记录`.
- Validate the last one or two days manually from the raw text before reporting, because the current day may have only the morning clock-in and no final clock-out yet.

## Overtime Rule

Weekday overtime starts at 19:00. For each Monday-Friday attendance day:

```text
daily_overtime = max(0, last_clock_time - 19:00)
```

Saturday/Sunday attendance also counts as overtime. For each weekend attendance day with at least two valid clock times, count the attended overlap with 09:00-18:00:

```text
daily_overtime = max(0, min(last_clock_time, 18:00) - max(first_clock_time, 09:00))
```

Calculate in minutes and only convert to hours/minutes at the end. Do not round away remaining minutes. Add weekday and weekend overtime minutes into one monthly total.

Examples:

- Last clock at 20:00 -> 1:00 overtime.
- Last clock at 20:40 -> 1:40 overtime.
- Two days ending 20:40 and 20:20 -> 1:40 + 1:20 = 3:00 total.
- Saturday clocked 08:30 and 18:30 -> 9:00 overtime.
- Sunday clocked 10:00 and 17:30 -> 7:30 overtime.

If the HR page displays evening times as short 12-hour text such as `8:40`, treat it as 20:40 only when the row/context clearly indicates it is the evening final clock. When using the helper script for that format, pass `--short-evening`.

## Helper Script

Use `scripts/overtime_calculator.py` when attendance data is available as copied text, CSV, or TSV. It extracts dates and clock times, selects the latest clock time per row, and totals overtime minutes.

```bash
python3 scripts/overtime_calculator.py attendance.csv
python3 scripts/overtime_calculator.py attendance.txt --short-evening
```

Use `scripts/hr_daily_blocks_to_rows.py` when the HR page was collected as daily raw blocks separated by `===== YYYY-MM-DD =====`. It emits one row per day for the overtime calculator:

```bash
python3 scripts/hr_daily_blocks_to_rows.py august_raw.txt august_rows.txt
python3 scripts/overtime_calculator.py august_rows.txt
```

Use `scripts/hr_attendance_collector.js` for the full HR browser collection flow. It emits `attendance_raw.txt`, `attendance_rows.txt`, and `attendance_final.png` in the selected output directory:

```bash
node scripts/hr_attendance_collector.js --year 2026 --month 8 --out-dir /tmp/quectel-hr-2026-08
python3 scripts/overtime_calculator.py /tmp/quectel-hr-2026-08/attendance_rows.txt
```

The script prints a daily table and a final total. Inspect questionable rows manually if the HR export uses unusual labels, multiple shift sections, missing clock-outs, or ambiguous 12-hour times.
