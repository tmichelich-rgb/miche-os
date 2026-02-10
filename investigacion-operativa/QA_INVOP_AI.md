# INVOP AI - QA Diario

## Objetivo
Testear invop.ai simulando distintos tipos de usuarios y encontrar casos límite, UX issues, y oportunidades de mejora en el flujo conversacional.

## Instrucciones para el QA

Abrí https://invop.ai en Chrome y ejecutá los siguientes escenarios de prueba. Para cada uno, registrá si la respuesta fue correcta, si los ejemplos contextuales fueron relevantes, y cualquier issue encontrado.

---

## Batería de Tests

### 1. Programación Lineal - Variedad de industrias
Probá decir estos productos y verificá que el ejemplo de recursos se adapte:

| Input del usuario | Ejemplo esperado (categoría) |
|---|---|
| "vendo remeras y musculosas" | Tela, costura, máquina (textil) |
| "hago pan y medialunas" | Harina, azúcar, manteca (comida) |
| "fabrico mesas y sillas" | Madera, carpintería, barniz (mueble) |
| "produzco caños y varillas" | Acero, soldadura, tornería (metal) |
| "ofrezco servicios de consultoría y capacitación" | Horas de trabajo, presupuesto (genérico) |
| "hago tortas y empanadas" | Harina, azúcar, manteca (comida) |
| "fabrico jeans y camperas" | Tela, costura, máquina (textil) |

### 2. Detección de módulo
| Input | Módulo esperado |
|---|---|
| "1" o "hola" | Debería preguntar qué módulo |
| "quiero saber cuánto pedir" | Inventarios |
| "tengo mucha fila en mi local" | Teoría de Colas |
| "quiero maximizar mis ganancias" | Programación Lineal |

### 3. Flujo completo LP
Seguir el flujo completo de un problema de LP:
1. Decir los productos
2. Dar los recursos
3. Dar el consumo
4. Dar las ganancias
5. Verificar que resuelve correctamente

### 4. Edge Cases de lenguaje
- Escribir todo en mayúsculas
- Escribir con errores ortográficos ("remera" vs "rremera")
- Usar slang ("hago buzos re piolas")
- Mezclar español e inglés
- Dar datos incompletos
- Dar datos contradictorios

### 5. Flujo de login desde redes sociales
- Verificar que desde LinkedIn WebView NO aparezca "Dev Login"
- Verificar que el botón "Copiar link" funcione
- Verificar Google Sign-In en Chrome normal

### 6. Idioma
- Cambiar a inglés y verificar que los ejemplos se traduzcan
- Verificar que el flujo completo funcione en inglés

---

## Formato de reporte

Para cada issue encontrado:
```
**Issue:** [Descripción breve]
**Severidad:** Alta / Media / Baja
**Pasos para reproducir:** [1, 2, 3...]
**Resultado actual:** [Qué pasó]
**Resultado esperado:** [Qué debería pasar]
**Archivo afectado:** [index.html / engine.py / etc.]
**Línea aproximada:** [si se puede identificar]
```

---

## Historial de QA

### 2026-02-10
- **Issue encontrado:** El ejemplo de recursos no se adaptaba al producto del usuario. Siempre mostraba "harina, azúcar, manteca" aunque el usuario dijera "remeras".
- **Severidad:** Media
- **Fix:** Se creó `lpContextExample()` que detecta la categoría del producto (textil, comida, mueble, metal, genérico) y adapta los ejemplos.
- **Estado:** Resuelto
