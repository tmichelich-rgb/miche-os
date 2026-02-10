# INVOP AI - Setup Registro de Usuarios

## Paso a paso para conectar el registro de usuarios a Google Sheets

### 1. Crear la Google Sheet

1. Andá a [sheets.google.com](https://sheets.google.com) y creá una hoja nueva
2. Nombrala **"INVOP AI - Registro de Usuarios"**
3. En la fila 1, poné estos headers:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Timestamp | Nombre | Email | Foto | Session ID | User Agent | Source |

4. Copiá el **ID de la hoja** de la URL. Es la parte entre `/d/` y `/edit`:
   `https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit`

---

### 2. Crear el Google Apps Script

1. Andá a [script.google.com](https://script.google.com) y creá un proyecto nuevo
2. Nombralo **"INVOP AI Webhook"**
3. Borrá todo el contenido y pegá este código:

```javascript
const SHEET_ID = 'PEGAR_ACA_EL_ID_DE_TU_SHEET';

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();

    sheet.appendRow([
      data.timestamp || new Date().toISOString(),
      data.name || '',
      data.email || '',
      data.picture || '',
      data.session_id || '',
      data.user_agent || '',
      data.source || 'invop.ai'
    ]);

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'ok' }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({ status: 'INVOP AI Webhook activo' }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

4. Reemplazá `PEGAR_ACA_EL_ID_DE_TU_SHEET` con el ID que copiaste en el paso 1

---

### 3. Publicar el Apps Script como Web App

1. Clickeá **Implementar** > **Nueva implementación**
2. En tipo, elegí **App web**
3. Configurá:
   - **Ejecutar como:** Tu cuenta
   - **Quién tiene acceso:** **Cualquier persona**
4. Clickeá **Implementar**
5. Copiá la **URL de la implementación** (algo como `https://script.google.com/macros/s/ABC.../exec`)

---

### 4. Conectar con INVOP AI

Abrí `index.html` y buscá `INVOP_CONFIG`. Reemplazá:

```javascript
WEBHOOK_URL:'YOUR_GOOGLE_APPS_SCRIPT_URL'
```

por:

```javascript
WEBHOOK_URL:'https://script.google.com/macros/s/TU_URL_ACA/exec'
```

---

### 5. Configurar Google Sign-In (para produccion)

1. Andá a [console.cloud.google.com](https://console.cloud.google.com)
2. Creá un proyecto nuevo o seleccioná uno existente
3. Habilitá la **API de Google Identity Services**
4. Andá a **Credenciales** > **Crear credenciales** > **ID de cliente OAuth 2.0**
5. Tipo: **Aplicacion web**
6. En "Origenes autorizados de JavaScript" agregá:
   - `https://invop.ai`
   - `http://localhost` (para desarrollo)
7. Copiá el **Client ID** y pegalo en `INVOP_CONFIG.GOOGLE_CLIENT_ID`

---

### 6. Configurar Stripe (para pagos Pro)

1. Creá cuenta en [stripe.com](https://stripe.com)
2. Creá un **Payment Link** con:
   - Producto: "INVOP AI Pro"
   - Precio: $2.99/mes (recurrente)
3. Copiá el link y pegalo en `INVOP_CONFIG.STRIPE_LINK`

---

## Resumen de lo que hay que reemplazar en INVOP_CONFIG

```javascript
const INVOP_CONFIG = {
  FREE_LIMIT: 5,
  GOOGLE_CLIENT_ID: 'tu-client-id.apps.googleusercontent.com',
  STRIPE_LINK: 'https://buy.stripe.com/tu-link',
  WEBHOOK_URL: 'https://script.google.com/macros/s/tu-script/exec'
};
```
