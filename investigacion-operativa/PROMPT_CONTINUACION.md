# INVOP AI — Prompt de continuación

Copiá todo lo que está debajo de la línea y pegalo en la próxima conversación.

---

## Contexto del proyecto

Estoy construyendo **INVOP AI** (invop.ai), una plataforma web de Investigación Operativa que permite a usuarios sin formación matemática resolver problemas reales usando lenguaje natural. La app tiene 3 módulos: Programación Lineal (Simplex), Inventarios (EOQ) y Teoría de Colas (M/M/M).

### Estado actual

**Tecnología:** Single-file HTML (~128KB, 2225 líneas) con CSS, JS, solvers, y UI conversacional embebidos. Hosteado en **Netlify**, dominio **invop.ai** (comprado en GoDaddy, DNS apuntando a Netlify).

**Archivo principal:** En mi carpeta "Investigacion Operativa" hay un `index.html` (el que se deploya) y una carpeta `invop-deploy/` con una copia lista para arrastrar a Netlify.

### Lo que ya está implementado y funcionando:

1. **Landing page** con scroll storytelling: hero → 3 actividades → 3 preguntas → impacto en dinero → barrera de entrada → from/to (fórmulas vs lenguaje natural) → CTA
2. **CTA flotante** que aparece al hacer scroll pasando el hero
3. **Avatar SVG interactivo** con estados (idle, thinking, solved, error, collecting, confirm)
4. **Dark theme** con Inter font, gradientes purple/green
5. **3 solvers completos**: LP (Simplex), Stock (EOQ con sensibilidad), Queue (M/M/M con análisis económico y búsqueda de M óptimo)
6. **NLP extraction** para los 3 módulos — el usuario describe en lenguaje natural y el sistema extrae parámetros
7. **Google Sign-In** implementado con Google Identity Services
   - Client ID configurado: `759483082155-gf5uqdlf9kee6jo6dts46eu7lesdmcsu.apps.googleusercontent.com`
8. **Sistema de límites**: 5 problemas gratis, paywall en el 6to con popup Pro $2.99/mes
9. **Webhook a Google Sheet** para registro de usuarios que se loguean
   - Apps Script URL configurada: `https://script.google.com/macros/s/AKfycbywMqF3GzlkM0vNnjY6Zdz_c-XX9HoHG49uBYTdW9CCZ0ZjsRLHJUyz13hadTMpkCdYAg/exec`
   - Google Sheet ID: `1Bn1rnujllwa6t15S6WW69IVKZW34em3eKdtTzZ6t2P0`
10. **Activity Log** con export a Excel (SheetJS) o CSV, con logging de interacciones y solves
11. **Template Excel** de log: `INVOP_AI_Log_Template.xlsx`
12. **Documento de arquitectura** actualizado: `INVOP_AI_Arquitectura_Producto_v1.docx`

### INVOP_CONFIG actual:
```javascript
const INVOP_CONFIG={
 FREE_LIMIT:5,
 GOOGLE_CLIENT_ID:'759483082155-gf5uqdlf9kee6jo6dts46eu7lesdmcsu.apps.googleusercontent.com',
 STRIPE_LINK:'https://buy.stripe.com/YOUR_LINK', // ← PENDIENTE
 WEBHOOK_URL:'https://script.google.com/macros/s/AKfycbywMqF3GzlkM0vNnjY6Zdz_c-XX9HoHG49uBYTdW9CCZ0ZjsRLHJUyz13hadTMpkCdYAg/exec'
};
```

---

## NEXT STEPS (lo que quiero hacer hoy)

### 1. Stripe — Conectar pagos
- Mi cuenta de Stripe está en review (conectada a banco Mercury)
- Una vez aprobada, necesito:
  - Crear un **Payment Link** en Stripe para "INVOP AI Pro" a $2.99/mes recurrente
  - Pegar el link en `INVOP_CONFIG.STRIPE_LINK`
  - Actualizar el deploy en Netlify
- Guiame paso a paso cuando tenga acceso

### 2. Redes Sociales — Crear presencia
Quiero armar la presencia de INVOP AI en redes. Necesito que me ayudes con:

- **X (Twitter):** Bio, estrategia de contenido, primeros tweets
- **YouTube:** Nombre del canal, descripción, ideas para primeros videos (demos de la app resolviendo problemas reales)
- **Instagram:** Perfil, estética visual (que matchee con el dark theme purple/green de la app), ideas de posts/reels
- **TikTok:** Perfil, ideas de videos cortos mostrando la magia de "texto natural → solución matemática"

La identidad visual es: fondo oscuro (#0F0F1A), purple (#6C3CE1 / #8B5CF6), verde accent (#06D6A0), font Inter.

---

Empecemos por lo que esté listo (Stripe si ya fue aprobado, o redes sociales).
