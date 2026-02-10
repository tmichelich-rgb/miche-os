// ═══════════════════════════════════════════════════════════
// INVOP AI — Google Apps Script Webhook (v2)
// Copia este código en tu Google Apps Script y re-deployá
// ═══════════════════════════════════════════════════════════

const SHEET_ID = '1Bn1rnujllwa6t15S6WW69IVKZW34em3eKdtTzZ6t2P0';

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.openById(SHEET_ID);
    const event = data.event || 'user_register';

    if (event === 'page_visit') {
      // ── Track page visits in "Visitas" sheet ──
      let visitSheet = ss.getSheetByName('Visitas');
      if (!visitSheet) {
        visitSheet = ss.insertSheet('Visitas');
        visitSheet.appendRow(['timestamp', 'referrer', 'url', 'session_id', 'user_agent']);
        // Bold headers
        visitSheet.getRange(1, 1, 1, 5).setFontWeight('bold');
      }
      visitSheet.appendRow([
        data.timestamp || new Date().toISOString(),
        data.referrer || 'direct',
        data.url || '',
        data.session_id || '',
        data.user_agent || ''
      ]);
    }
    else if (event === 'upgrade_pro') {
      // ── Track Pro upgrades in "Usuarios" sheet (update existing row) ──
      const userSheet = ss.getSheetByName('Usuarios') || ss.getActiveSheet();
      const emails = userSheet.getRange('C2:C').getValues().flat();
      const rowIndex = emails.indexOf(data.email);
      if (rowIndex > -1) {
        userSheet.getRange(rowIndex + 2, 8).setValue('TRUE'); // Column H = pro
      }
    }
    else {
      // ── Register new user in "Usuarios" sheet ──
      const userSheet = ss.getSheetByName('Usuarios') || ss.getActiveSheet();

      // Check if user already exists (avoid duplicates)
      const emails = userSheet.getRange('C2:C').getValues().flat();
      const alreadyExists = emails.includes(data.email);

      if (!alreadyExists) {
        userSheet.appendRow([
          data.timestamp || new Date().toISOString(),
          data.name || '',
          data.email || '',
          data.picture || '',
          data.source || 'invop.ai',
          data.session_id || '',
          data.user_agent || '',
          data.pro || false
        ]);
      }
    }

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'ok', event: event }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    // Log error for debugging
    console.error('INVOP Webhook Error:', err.toString());
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  try {
    const ss = SpreadsheetApp.openById(SHEET_ID);
    const userSheet = ss.getSheetByName('Usuarios') || ss.getActiveSheet();
    const data = userSheet.getDataRange().getValues();
    const headers = data[0];
    const users = data.slice(1).map(row => {
      const obj = {};
      headers.forEach((h, i) => obj[h] = row[i]);
      return obj;
    });

    // Also get visit count
    let visitCount = 0;
    const visitSheet = ss.getSheetByName('Visitas');
    if (visitSheet) {
      visitCount = Math.max(0, visitSheet.getLastRow() - 1);
    }

    return ContentService
      .createTextOutput(JSON.stringify({
        users: users,
        user_count: users.length,
        visit_count: visitCount
      }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
