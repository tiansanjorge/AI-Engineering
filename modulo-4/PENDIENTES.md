# Pendientes, problemas conocidos y posibles mejoras

Registro de lo que se detecta mientras se construye el Módulo 4 y **no se resuelve en el momento**
(se revisa todo junto al terminar). Cada ítem lleva evidencia, impacto e ideas. Lo resuelto se
marca como tal, no se borra.

| ID | Área | Resumen | Prioridad | Estado |
|---|---|---|---|---|
| P-01 | Evaluación | El par 3 (escaneo degradado) se lee igual de bien que el limpio: no discrimina | Media | Resuelto |
| P-02 | Modelo de datos | «Cero cambios» se trata como error: una adenda solo administrativa falla la validación | Baja | Abierto |
| P-03 | Corpus | Contratos sintéticos y digitales, de una sola página, un solo idioma | Media | Abierto |
| P-04 | Parsing / seguridad | Con escaneos muy malos el modelo INVENTA datos plausibles en vez de marcar `[ilegible]` | Alta | Abierto |
| P-05 | Parsing | Una negativa del modelo («no puedo ayudar…») se acepta como transcripción válida | Alta | Resuelto |
| P-06 | Parsing | Errores silenciosos de dígitos con escaneos malos (2025 leído como 2023) | Alta | Abierto |

---

## P-01 · El par 3 no estresaba al parser (RESUELTO)

- **Qué pasaba:** con la degradación original (nivel 1) el WER era idéntico al de las imágenes
  limpias: el par 3 no discriminaba.
- **Qué se hizo:** `degrade()` ahora tiene 5 niveles de severidad (rotación, desenfoque, ruido,
  resolución, sombra y compresión JPEG) y `scripts/stress_parsing.py` mide la curva de quiebre sobre
  las dos adendas (`outputs/parsing_stress.json`, imágenes en `data/stress_scans/`).
- **Curva medida (WER medio de las 2 adendas):** nivel 1 → 0,000 · nivel 2 → 0,000 ·
  **nivel 3 → 0,046** (errores de dígitos, datos clave intactos) · nivel 4 → 0,38 (datos clave
  perdidos o inventados) · nivel 5 → 0,97 (el modelo se niega a transcribir).
- **Resultado:** el par 3 usa el **nivel 3**, el primero con errores reales: WER 0,017 (original) y
  0,029 (adenda). Además, la normalización del WER ignora el largo de la línea de firma (`____`).

## P-04 · Con escaneos muy malos el modelo inventa datos (ALTA)

- **Qué pasa:** en el nivel 4 el parser devolvió fechas («2015») y un monto («$ 50.000») que no
  están en el documento, y cambió el nombre de una empresa, todo plausible y SIN `[ilegible]`, aunque
  el prompt lo prohíbe. La regla del prompt no alcanza.
- **Evidencia:** `data/stress_scans/nivel4_par1_adenda.jpg` (reproducible con
  `scripts/stress_parsing.py`).
- **Impacto:** en un contexto legal es el peor tipo de falla: un dato falso con aspecto de verdadero,
  que los agentes siguientes toman como cierto.
- **Ideas:** (1) controles de coherencia entre ambos textos (la adenda debe citar la fecha y las
  partes del contrato original; si no coinciden, marcar para revisión humana); (2) pedir al
  modelo una autoevaluación de legibilidad y rechazar bajo un umbral; (3) doble lectura y comparar;
  (4) preprocesar la imagen (enderezar, aumentar contraste) antes de enviarla; (5) un chequeo de
  calidad de imagen previo (nitidez, resolución) que rechace entradas inservibles.

## P-05 · Una negativa se acepta como transcripción (RESUELTO)

- **Qué pasa:** en el nivel 5 el modelo respondió «Lo siento, no puedo ayudar con el contenido de la
  imagen» y `parse_contract_image` lo devolvió como texto válido, que pasaría al agente 1.
- **Qué se hizo:** `_is_refusal()` en `image_parser.py` mira el campo `refusal` de la API y, como
  respaldo, un patrón de frases de negativa en respuestas cortas (≤ 300 caracteres, para no confundir
  un contrato real). Lanza `EmptyParseError`. Verificado con la imagen real del nivel 5.
- **Límite:** el patrón cubre español e inglés; una negativa con otra redacción podría colarse.

## P-06 · Errores silenciosos de dígitos

- **Qué pasa:** en el nivel 3, «2025» salió como «2023» en las tres menciones de la adenda 1, sin
  advertencia. Los datos clave (2026, 2.800) sobrevivieron, pero una fecha equivocada altera la
  interpretación legal.
- **Ideas:** las mismas de P-04 (coherencia entre documentos, doble lectura).

## P-02 · «Cero cambios» es un error

- **Qué pasa:** `ExtractionResult` exige al menos un cambio. Una adenda legítima sin cambios
  sustantivos (p. ej. solo cambia el domicilio) no produciría un resultado válido.
- **Ideas:** distinguir «el modelo no encontró nada» de «la adenda no cambia nada» con un campo
  explícito, en vez de listas vacías.

## P-03 · Corpus acotado

- **Qué pasa:** 3 pares sintéticos, una página, español. No cubre tablas, firmas manuscritas,
  sellos, varias páginas ni otros idiomas.
