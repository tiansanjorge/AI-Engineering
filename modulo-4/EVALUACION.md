# Evaluación del sistema

Qué se midió, cómo, con qué resultados y qué se iteró a partir de ello. Todo es reproducible y la
evidencia cruda está en `outputs/`.

## Método

- **Ground truth escrito antes de correr nada:** cada par trae su `expected.json` (cambios esperados
  con sección y tipo, datos clave del resumen, cláusulas que NO deben figurar como cambiadas).
- **Métricas deterministas** (sin LLM-juez; `src/evaluation.py`, con tests):
  cobertura de secciones (recall), falsos positivos (todo lo reportado que no corresponde a un
  cambio esperado), tipo de cambio acertado (adición / eliminación / modificación), datos clave en
  el resumen, y muletilla (el resumen habla del mapa o de las alertas sin que las haya).
- **Repeticiones:** 3 corridas por par; el modelo no es determinista y una sola corrida no prueba
  nada. «Estable» = las 3 corridas reportan exactamente el mismo conjunto de secciones.
- **Camino real completo:** imagen → parseo → agente 1 → agente 2 → JSON (`scripts/run_eval.py`),
  con `gpt-4o`. Las corridas se agrupan en una sesión de Langfuse.

## Resultados (prompt final)

### Camino completo, 3 pares × 3 corridas (`outputs/eval_e2e.json`)

| Par | Perfectas | Recall | Tipo de cambio | Falsos + | Datos clave | Estable | ~Latencia | ~Tokens |
|---|---|---|---|---|---|---|---|---|
| 1 · simple | 3/3 | 100 % | 100 % | 0 | 100 % | sí | 10-11 s | 7,4 k |
| 2 · complejo | 3/3 | 100 % | 100 % | 0 | 100 % | sí | 11-13 s | 7,9 k |
| 3 · escaneo degradado (nivel 3) | 3/3 | 100 % | 100 % | 0 | 100 % | sí | 11 s | 6,9 k |

En el par 3 el agente 1 detectó la lectura errónea del parser (2025 → 2023) y el resumen cerró con
«Advertencia:» las 3 veces.

### Escaneos peores, camino completo (`outputs/stress_e2e.json`)

Original limpio + adenda degradada del par 1, 3 corridas por nivel:

| Nivel | Advertencia en el resumen | Datos clave correctos | Qué pasa |
|---|---|---|---|
| 3 | 3/3 | 2/2 | Lee mal alguna fecha, avisa; los datos relevantes son correctos |
| 4 | 3/3 | **0/2** | El parser inventa fechas, partes y monto; el resumen los presenta como reales **pero cierra avisando** inconsistencias de fechas y nombres |

Lectura honesta: el sistema **detecta pero no corrige**. La detección funciona porque fechas y partes
se pueden cruzar con el contrato original; un monto inventado no tiene contra qué cruzarse (en el
nivel 4 se salvó porque otros datos delataron el problema). Ver `PENDIENTES.md`, P-04 y P-06.

## Historia de iteración (cada cambio nació de una medición)

| # | Hallazgo | Evidencia | Cambio | Resultado |
|---|---|---|---|---|
| 1 | El par 3 no discriminaba: el escaneo «malo» se leía igual que el limpio | WER 0,008-0,015 en las 6 imágenes | Escala de 5 niveles de degradación + prueba de estrés del parser | Punto de quiebre ubicado en el nivel 3-4; par 3 pasa al nivel 3 |
| 2 | Con escaneos muy malos el parser inventa datos / se niega a transcribir | `outputs/parsing_stress.json` | Guarda contra negativas (`_is_refusal`); mitigación vía agente 1 | Negativa → `EmptyParseError`; la alucinación queda como pendiente documentado |
| 3 | La evaluación de falsos positivos no detectaba un inciso espurio (4.1 junto al 4.3) | Test que lo reproduce | Todo lo reportado sin cambio esperado cuenta como extra | Métrica más estricta |
| 4 | El resumen terminaba con una muletilla («No hay alertas en el mapa contextual») pese a la regla del prompt | Primera corrida real; luego 2/9 corridas lo mostraron tras un primer refuerzo (`outputs/eval_e2e_prompt_v2.json`: par 1 con 1/3 perfectas) | Regla 7: el resumen nunca habla del mapa ni de las alertas; métrica `has_filler` | 9/9 perfectas, 0 muletillas |
| 5 | El verificador de trazas daba 4 fallas falsas (leía mal el campo `model`) | 36/40 → 40/40 | Pedir `fields=...,model` a la API | Auditoría de traza 40/40 |
| 6 | Con credenciales de Langfuse ausentes/inválidas el análisis corría (gastando tokens) y se caía al final al pedir la URL de la traza, perdiendo el resultado | Corrida real con claves vacías: `UnauthorizedError` | `safe_trace_url` y `flush` que nunca lanzan (+ test) | Exit 0, JSON impreso, solo se omite el link |
| 7 | La revisión de código (10 hallazgos) encontró, entre otros: un archivo corrupto con extensión `.png` pasaba la validación inicial y explotaba luego con traceback de Pillow; los hechos clave se comparaban por subcadena (`'2.800'` coincidía dentro de `'12.800'`, dando por correcto un valor inventado); los scripts de evaluación perdían las corridas pagadas ante un fallo | Tests que reproducen cada caso | Integridad de imagen dentro de `validate_image` (ambas imágenes, antes de gastar); `contains_fact` con límites; evidencia guardada siempre (`finally`); estado del agente reiniciado por corrida | 77 tests; evaluación real repetida con las métricas más estrictas: mismo 9/9 |

## Limitaciones declaradas

- **Set chico y sintético:** 3 pares escritos por mí, una página, español. 9/9 no demuestra
  generalización; demuestra que el diseño funciona en estos casos.
- **Sin set ciego:** los prompts se ajustaron mirando estos mismos casos (riesgo de sobreajuste). Un
  par nuevo, escrito después, sería la prueba más honesta.
- **Temperatura 0 no garantiza determinismo:** por eso se repite; aun así, 3 corridas son pocas.
- **Escaneos reales:** la degradación es simulada; un escaneo real (manchas, firmas manuscritas,
  sellos, varias páginas) puede comportarse distinto.
- **Costo:** se midieron tokens (~7-8 k por análisis); el costo en USD lo calcula Langfuse por
  generation (p. ej. USD 0,0076 la extracción del par 1).
