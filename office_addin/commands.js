/* Higgs Excel Add-in — command functions.
   Runs silently (no task pane). Reads Excel data and POSTs to the local Python backend.
   All user interaction happens on the desktop widget, not here.
*/

const ARIA_API = "http://localhost:5050";

Office.onReady();

// ── Helper: post JSON to backend ─────────────────────────────────────────────

async function postToAria(endpoint, payload) {
  try {
    const resp = await fetch(`${ARIA_API}${endpoint}`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
    return resp.ok;
  } catch (err) {
    console.error("[Aria] Failed to reach backend:", err);
    return false;
  }
}

// ── Button 1: Send selected range ─────────────────────────────────────────────

async function sendSelectionToAria(event) {
  try {
    await Excel.run(async (ctx) => {
      const range = ctx.workbook.getSelectedRange();
      const sheet = ctx.workbook.worksheets.getActiveWorksheet();

      range.load(["address", "values", "formulas", "rowCount", "columnCount"]);
      sheet.load("name");
      await ctx.sync();

      // Trim to reasonable size: max 30 rows × 20 cols
      const values   = range.values.slice(0, 30).map(r => r.slice(0, 20));
      const formulas = range.formulas.slice(0, 30).map(r => r.slice(0, 20));

      // Detect if first row looks like a header
      const hasHeader = values.length > 1 && values[0].every(
        (cell) => typeof cell === "string" && cell.trim() !== ""
      );

      const payload = {
        sheet:      sheet.name,
        address:    range.address,
        row_count:  range.rowCount,
        col_count:  range.columnCount,
        has_header: hasHeader,
        values:     values,
        formulas:   formulas,
        source:     "selection",
      };

      const ok = await postToAria("/api/excel/selection", payload);
      if (ok) {
        // Brief visual feedback: show a toast via Office notification
        Office.context.ui.displayDialogAsync(
          `${ARIA_API}/addin/sent.html`,
          { height: 12, width: 18, displayInIframe: true },
          (result) => {
            if (result.value) {
              setTimeout(() => result.value.close(), 1800);
            }
          }
        );
      }
    });
  } catch (err) {
    console.error("[Aria] sendSelectionToAria error:", err);
  }
  event.completed();
}

// ── Button 2: Send sheet summary (headers + row count + used range) ───────────

async function sendSheetSummaryToAria(event) {
  try {
    await Excel.run(async (ctx) => {
      const sheet      = ctx.workbook.worksheets.getActiveWorksheet();
      const usedRange  = sheet.getUsedRange();

      sheet.load("name");
      usedRange.load(["address", "rowCount", "columnCount", "values"]);
      await ctx.sync();

      // First row as headers, first 5 rows as sample
      const headers = usedRange.values[0] || [];
      const sample  = usedRange.values.slice(0, 5);

      // Column stats: count non-empty cells per column
      const col_counts = headers.map((_, ci) =>
        usedRange.values.filter(row => row[ci] !== "" && row[ci] !== null).length
      );

      const payload = {
        sheet:      sheet.name,
        address:    usedRange.address,
        row_count:  usedRange.rowCount,
        col_count:  usedRange.columnCount,
        headers:    headers,
        sample:     sample,
        col_counts: col_counts,
        source:     "sheet_summary",
      };

      const ok = await postToAria("/api/excel/selection", payload);
      if (ok) {
        Office.context.ui.displayDialogAsync(
          `${ARIA_API}/addin/sent.html`,
          { height: 12, width: 18, displayInIframe: true },
          (result) => {
            if (result.value) {
              setTimeout(() => result.value.close(), 1800);
            }
          }
        );
      }
    });
  } catch (err) {
    console.error("[Aria] sendSheetSummaryToAria error:", err);
  }
  event.completed();
}
