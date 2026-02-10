# INVOP AI — Listado Completo de Funcionalidades
## Desarrollado en ~14 horas con AI | 3,298 líneas de código | 1 solo archivo HTML

---

## ARQUITECTURA & CORE (5)
1. **Single-file HTML app** — Toda la app (CSS + JS + solvers + NLP + UI) en un solo archivo de 2,969 líneas
2. **Dark theme design system** — Variables CSS customizadas, paleta púrpura + verde + gradientes
3. **Responsive mobile-first** — Breakpoints para mobile (768px), tablet y desktop
4. **Progressive Web App ready** — Funciona offline una vez cargada, localStorage para persistencia
5. **Zero-dependency architecture** — Sin frameworks, sin build tools, vanilla HTML/CSS/JS

---

## LANDING PAGE (12)
6. **Hero section animada** — Texto con gradientes animados, radial backgrounds
7. **Sección "3 Actividades"** — Grid de 3 columnas con pillar cards hover effects
8. **Sección "3 Preguntas Clave"** — Cards numeradas con gradient overlay
9. **Sección "Impacto Económico"** — 3 impact cards con estadísticas reales (15-30%, 20-40%, 35-50%)
10. **Sección "La Barrera"** — 4 íconos de barrera (Ingeniería, Modelos, Software, Licencias)
11. **Sección "From → To"** — 3 transformaciones con fórmulas vs. lenguaje natural
12. **CTA final** — Call-to-action con gradiente y botón principal
13. **Scroll animations** — IntersectionObserver con fade-up y staggered delays
14. **Floating CTA button** — Aparece al scrollear, desaparece en app mode, pulse animation
15. **Smooth scroll navigation** — "Descubrí cuáles" scroll suave a contenido
16. **Language toggle en landing** — ES | EN switch visible en header
17. **From/To examples bilingües** — Panadería/bakery, caños PVC/PVC pipes, clínica/clinic

---

## 12 ANIMACIONES CSS (12)
18. **Float** — Scroll hint bouncing
19. **Fade-up** — Scroll-triggered con 3 delays staggered
20. **msgIn** — Mensajes nuevos con fade + scale (cubic-bezier)
21. **Bounce** — Typing indicator dots
22. **Avatar ring spin** — Rotación continua 8s
23. **Avatar thinking spin** — Rotación acelerada 1.5s
24. **Pulse-ring** — Estado "resuelto" opacity pulse
25. **Pulse-dot** — Indicador status scale pulse
26. **ctaPulse** — CTA flotante ring pulse 2s
27. **pls** — Send button loading pulse
28. **modalIn** — Modal entrada scale + translateY
29. **Hover transforms** — translateY(-2px to -4px) en todas las cards

---

## SISTEMA DE AUTH (6)
30. **Google Identity Services (GIS)** — Integración completa con OAuth 2.0
31. **Rendered Google Sign-In button** — Botón oficial de Google renderizado directamente
32. **JWT token parsing** — parseJwt() extrae nombre, email, foto del token
33. **Sesión persistente** — localStorage mantiene login entre sesiones
34. **User pill UI** — Avatar circular + nombre en header, clickeable
35. **Dev mode fallback** — Login de desarrollo cuando GIS no está disponible

---

## MOTOR DE RESOLUCIÓN — PROGRAMACIÓN LINEAL (10)
36. **Simplex completo (2 fases)** — Algoritmo revisado con variables artificiales Big-M
37. **Restricciones ≤, ≥, =** — Maneja los 3 tipos de restricciones
38. **Detección de problemas no acotados** — Identifica cuando Z → ∞
39. **Detección de problemas infactibles** — Artificial variables permanecen en base
40. **Precios sombra (dual values)** — Shadow prices para cada restricción
41. **Variables de holgura** — Calcula slack/surplus por restricción
42. **Identificación de cuellos de botella** — Marca restricciones binding
43. **Análisis de sensibilidad LP** — Rangos de coeficientes y RHS
44. **Multi-periodo (Wagner-Whitin)** — Producción + inventario por período
45. **Resumen de decisión ejecutiva** — "Producí X unidades de A, Y de B..."

---

## MOTOR DE RESOLUCIÓN — INVENTARIOS EOQ (6)
46. **EOQ básico (Miranda Cap.2)** — q* = √(2kD/Tc₁)
47. **EOQ con faltante (Miranda Cap.4)** — Backorders con costo c₂
48. **Stock de seguridad** — Cálculo de safety stock (Sp)
49. **Punto de reorden** — SR = LT·(D/T) + Sp
50. **Desglose de costos** — Adquisición + pedido + almacenamiento + protección
51. **Tabla de sensibilidad** — Variación ±30% de cada parámetro

---

## MOTOR DE RESOLUCIÓN — TEORÍA DE COLAS (8)
52. **Modelo M/M/1** — Server único, capacidad infinita
53. **Modelo M/M/1/N** — Server único, capacidad finita
54. **Modelo M/M/s** — Multi-servidor, capacidad infinita
55. **Modelo M/M/s/N** — Multi-servidor, capacidad finita
56. **Métricas completas** — ρ, P₀, L, Lc, W, Wc, H
57. **Distribución de probabilidades** — P(n) para n=0 a 20
58. **Análisis económico** — Evalúa M-1 a M+5 servidores, encuentra óptimo
59. **Detección de inestabilidad** — ρ ≥ 1 warning con recomendación

---

## PROCESAMIENTO DE LENGUAJE NATURAL (10)
60. **Detección automática de módulo** — 116 keywords (49 LP + 25 Stock + 42 Colas)
61. **Extracción de productos LP** — Detecta nombres de regex: "panadería hace pan, medialunas y tortas"
62. **Extracción de recursos LP** — 4 patrones: "100 kg de harina disponibles"
63. **Extracción de consumos LP** — "Para un pan necesito 0.5 kg de harina"
64. **Extracción de precios LP** — Precio de venta, costo variable, ganancia
65. **Matching fuzzy de recursos** — Normalización de nombres (acentos, mayúsculas, parcial)
66. **Extracción de parámetros Stock** — 7 parámetros desde texto libre
67. **Extracción de parámetros Colas** — 5+ parámetros con conversión de unidades
68. **Normalización de números** — "1.500" = 1500, "1,5" = 1.5 (formato argentino)
69. **Detección multi-período** — Reconoce "mes 1: 200, mes 2: 350..." automáticamente

---

## CHAT INTERFACE (11)
70. **Mensajes usuario** — Burbuja púrpura degradé, alineada derecha
71. **Mensajes asistente** — Card oscura con avatar label
72. **Typing indicator** — 3 dots animados con bounce staggered
73. **Markdown rendering custom** — Bold, italic, tablas, listas
74. **Tablas formateadas** — Striped rows, header highlight
75. **Avatar con 5 moods** — idle, listening, thinking, solved, error
76. **Mood text bilingüe** — "Listo para resolver" / "Ready to solve"
77. **Auto-resize textarea** — Crece con el contenido (44px a 150px)
78. **3 example cards** — Click para enviar problema pre-armado
79. **Quick question buttons** — Sensibilidad, fórmulas, nuevo problema
80. **Enter to send** — Shift+Enter para newline

---

## FLUJO CONVERSACIONAL (7)
81. **State machine de 5 stages** — detect → collect → lp_input → confirm → solved
82. **Memoria multi-turno** — Acumula datos a lo largo de la conversación
83. **Confirmación antes de resolver** — Muestra modelo armado, usuario aprueba
84. **Assumptions tracking** — Registra todas las suposiciones implícitas
85. **Fallback inteligente** — Pide dato faltante específico
86. **Post-solve actions** — "sensibilidad", "fórmulas", "nuevo" como follow-ups
87. **Ajuste de datos** — "No, cambiar X" vuelve a collect sin perder todo

---

## SISTEMA BILINGÜE i18n (8)
88. **307 claves de traducción** — ES y EN completos
89. **data-i18n para textContent** — Atributo en ~50 elementos HTML
90. **data-i18n-html para innerHTML** — Templates complejos con gradientes y links
91. **t() helper function** — Lookup con fallback al key original
92. **tMsg() para chat** — Templates de mensajes conversacionales
93. **Detección automática de idioma** — navigator.language en first load
94. **Persistencia de idioma** — localStorage 'invop_lang'
95. **Todo bilingüe** — Módulos, stages, examples, paywall, errors, moods

---

## SISTEMA FREEMIUM & STRIPE (9)
96. **Contador de uso** — localStorage trackea problemas resueltos
97. **Límite free: 3 problemas** — Configurable via INVOP_CONFIG.FREE_LIMIT
98. **Paywall modal** — Usage bar + pricing card + features list
99. **Stripe Payment Links** — Sin SDK client-side, redirect directo
100. **Pre-filled email** — Pasa email del usuario al checkout
101. **Client reference ID** — Identifica usuario en Stripe
102. **Post-payment activation** — ?payment_success=true → activa Pro
103. **Pro badge ✨** — Aparece junto al nombre del usuario
104. **Precio $3.99/mes** — Mostrado en paywall

---

## ANALYTICS & LOGGING (5)
105. **Activity log completo** — Timestamp, módulo, input, params, solución, status
106. **Export a Excel (.xlsx)** — Via SheetJS, descarga directa del browser
107. **Export a CSV** — Formato alternativo
108. **Session ID tracking** — UUID por sesión
109. **Log counter bilingüe** — "3 eventos registrados" / "3 events logged"

---

## WEBHOOK & BACKEND (4)
110. **Google Apps Script** — doPost() + doGet() endpoints
111. **Registro de usuarios** — POST automático al loguearse
112. **Dashboard data API** — GET ?action=dashboard retorna JSON
113. **Pro upgrade tracking** — Evento 'upgrade_pro' al pagar

---

## DASHBOARD ANALYTICS (8)
114. **4 KPI cards** — Usuarios, Solves, Pro%, MRR
115. **Gráfico de uso por módulo** — Bar chart horizontal (LP, Inventarios, Colas)
116. **Desglose de costos** — Netlify, dominio, OAuth, Stripe, LLM
117. **Simulador de escala** — Sliders interactivos para proyecciones
118. **Sistema de alertas** — Umbrales de costo LLM, queries, Stripe fees
119. **Tabla de usuarios** — Últimos 20 registros desde Google Sheets
120. **Tech stack cards** — 6 secciones documentando la arquitectura
121. **Pre-scale checklist** — 7 items de preparación

---

## SOCIAL MEDIA & MARKETING (5)
122. **Estrategia completa** — Documento de 12 secciones (audiencia, pilares, calendario, KPIs)
123. **Contenido Semana 1** — Spreadsheet con 3 hojas (calendario, IG, X)
124. **Carousels IG bilingües** — 2 series de 7 slides cada una (ES + EN)
125. **Reel scripts** — 30s scripts con timestamps (ES + EN)
126. **Tweets y threads** — 12 singles + 3 threads de 5-6 tweets (ES + EN)

---

## SIDEBAR & UX (5)
127. **Module selector** — 3 botones (LP, STOCK, QUEUE) con highlight
128. **Pipeline progress** — 6 dots con estados visuales (gris → verde)
129. **Parameters panel** — Muestra parámetros extraídos en tiempo real
130. **Activity log panel** — Lista de eventos con export button
131. **Collapsible sidebar** — Se oculta en mobile

---

## TOTAL: 131 funcionalidades
- **3,298 líneas de código** (2,969 app + 329 dashboard)
- **70+ funciones JavaScript**
- **307 claves de traducción**
- **116 keywords de detección NLP**
- **50+ patrones regex** de extracción
- **12 animaciones CSS**
- **5 modelos matemáticos** de resolución
- **2 idiomas** completos
- **1 solo archivo HTML** para toda la app
