# INVOP AI — Prompt de continuación (Redes Sociales + Stripe)

Copiá todo lo de abajo y pegalo en la próxima conversación:

---

## Contexto

Soy Tomas. Estoy lanzando **INVOP AI** (invop.ai), una plataforma web que resuelve problemas de Investigación Operativa con lenguaje natural. El usuario describe su problema como se lo contaría a un colega y la app arma el modelo matemático, lo resuelve y le da una decisión ejecutiva accionable.

### Producto

- **3 módulos**: Programación Lineal (Simplex), Inventarios (EOQ), Teoría de Colas (M/M/M)
- **Single-file HTML** (~130KB) hosteado en **Netlify**, dominio **invop.ai** (GoDaddy → Netlify DNS)
- **Google Sign-In** configurado y funcionando
- **Freemium**: 5 problemas gratis, después paywall Pro $2.99/mes
- **Webhook** a Google Sheet que registra cada usuario que se loguea
- **Stripe** pendiente (cuenta en review con Mercury Bank, debería estar aprobada)

### Identidad visual
- Fondo oscuro: `#0F0F1A`
- Purple principal: `#6C3CE1` / `#8B5CF6`
- Verde accent: `#06D6A0`
- Font: Inter
- Avatar SVG animado con estados de ánimo
- Landing con scroll storytelling (hero → actividades → preguntas → impacto → barrera → from/to → CTA)

### Propuesta de valor
"Hasta ahora para resolver problemas de operaciones necesitabas ser ingeniero y tener software caro. INVOP AI lo pone al alcance de cualquiera: describí tu problema y recibí la decisión óptima."

### Público objetivo
- Dueños de PyMEs (panaderías, distribuidores, clínicas, etc.)
- Gerentes de operaciones sin background técnico
- Estudiantes de ingeniería/administración
- Consultores operativos

---

## Lo que quiero hacer ahora

### 1. Stripe — Conectar pagos (si ya fue aprobado)
- Crear Payment Link: "INVOP AI Pro" $2.99/mes recurrente
- Actualizar `INVOP_CONFIG.STRIPE_LINK` en el index.html
- Re-deployar a Netlify

### 2. Redes Sociales — Crear presencia completa

Para cada red quiero:
- Nombre de usuario / handle sugerido
- Bio optimizada
- Estrategia de contenido (qué tipo de posts, frecuencia)
- Ideas concretas para los primeros 5-10 posts/videos
- Hashtags clave

**Redes:**

- **X (Twitter)**: Para posicionamiento profesional, hilos técnicos simplificados, engagement con comunidad de startups/IO/operaciones
- **YouTube**: Demos en video de la app resolviendo problemas reales, mini-tutoriales, "antes vs después" de tomar decisiones con datos
- **Instagram**: Visual, reels cortos, infografías sobre impacto de decisiones operativas, behind the scenes del producto
- **TikTok**: Videos ultra-cortos mostrando la "magia" de escribir un problema en texto y que salga la solución óptima, formato problema→solución

### Tono de comunicación
- Accesible, no académico
- "Tu negocio ya tiene las respuestas, solo falta hacerle las preguntas correctas"
- Mostrar que IO no es solo para ingenieros
- Datos duros de impacto (+15-30% margen, -20-40% costos inventario, -35-50% costos espera)

---

Empecemos por lo que esté listo. Si Stripe está aprobado arrancamos por ahí, si no vamos directo a redes.
