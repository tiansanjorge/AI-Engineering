# Reporte del Proyecto Integrador — Módulo 1

## Arquitectura

El sistema es un único entrypoint CLI (`src/run_query.py`) con tres
responsabilidades separadas:

- `src/llm_client.py` — arma el prompt (system prompt desde
  `prompts/main_prompt.txt` + la pregunta del usuario) y llama a la API de
  Chat Completions de OpenAI con `response_format={"type": "json_object"}`,
  forzando al modelo a devolver un objeto JSON sintácticamente válido. Si la
  primera respuesta no parsea como JSON, hace **una llamada de reparación**
  (una segunda llamada barata, pidiéndole al modelo que arregle su propio
  JSON roto, con `temperature=0`) antes de rendirse — un patrón de dos
  pasos habitual para salidas estructuradas de un LLM (generar, y después
  reparar si hace falta), en vez de asumir que el primer intento siempre
  va a ser válido.
- `src/schema.py` — define el contrato de negocio (`answer`, `confidence`,
  `actions`, con `reasoning` opcional) independientemente de la validez
  sintáctica del JSON, y lo valida. También define `fallback_response`, una
  respuesta degradada segura que se usa cuando la salida del modelo no
  cumple el contrato ni siquiera después del intento de reparación.
- `src/metrics.py` — calcula `estimated_cost_usd` a partir de una tabla de
  precios estática y agrega una fila por ejecución a `metrics/metrics.csv`.

`run_query.py` conecta todo esto: nunca confía ciegamente en la salida del
modelo — valida el JSON parseado contra el contrato, y solo lo deja pasar
si es válido; si no, lo reemplaza por la respuesta de fallback y de todos
modos registra la ejecución (con `valid_json=False`), para que los fallos
sean auditables, no silenciosos.

## Técnica de prompting: elegida por medición, no por supuesto

La elección de técnica de prompt engineering se trata como una pregunta
empírica, no como un supuesto de diseño: *diseñar varias variantes de
prompt, medirlas en tokens/latencia/calidad, y recién ahí elegir una* — en
vez de elegir una técnica de entrada y justificarla después.
`src/compare_prompt_techniques.py`
implementa exactamente ese flujo como código real y reutilizable (no un
script descartable): define tres variantes de prompt **puras** en
`prompts/variants/` (zero-shot, few-shot, chain-of-thought — nunca
combinadas entre sí, para poder atribuirle el resultado a una sola
técnica) y corre las tres contra el mismo set de 5 preguntas de prueba que
cubre cada acción del catálogo, registrando cada resultado en
`metrics/prompt_comparison.csv`.

### Resultados reales (`gpt-4o-mini`, 15 llamadas, 3 variantes × 5 preguntas)

| variante | precisión | tokens promedio | latencia promedio (ms) | costo total (USD) |
|---|---|---|---|---|
| chain_of_thought | 100% | 553.6 | 1498.9 | 0.000633 |
| few_shot | 100% | 703.0 | 1222.3 | 0.000665 |
| zero_shot | 100% | 430.4 | 1605.9 | 0.000455 |

Las tres variantes empataron en precisión sobre este set de prueba — 5
preguntas es una muestra demasiado chica para diferenciarlas solo por
exactitud. Donde sí se diferencian es en costo: zero-shot es ~35% más
barato que few-shot y ~22% más barato que chain-of-thought, simplemente
porque no lleva ejemplos ni traza de razonamiento.

### Por qué se eligió chain-of-thought pese a no ser el más barato

Con la precisión empatada, el factor decisivo fue la **auditabilidad**, no
el costo bruto en tokens. Chain-of-thought es la única variante que
devuelve un campo `reasoning` — una lista corta de los pasos que siguió el
modelo antes de definir `confidence`/`actions`. En un producto de Help
Desk, un agente humano revisando un caso límite (confianza baja, una
escalada) necesita ver *por qué* el asistente llegó a esa conclusión, no
solo la conclusión en sí. El costo extra sobre zero-shot es marginal en
términos absolutos (~$0.0002 cada 1.000 preguntas adicionales) y menor que
el de few-shot, mientras que los tokens extra de few-shot (los ejemplos
resueltos) no compraron ninguna mejora medible de precisión en este set de
prueba. Esto sigue un principio general de ingeniería: no ir
directamente a la opción más cara por defecto, pero tampoco optimizar por
costo cuando eso resigna algo que el producto realmente necesita — acá,
eso es la traza de auditoría, no la exactitud bruta.

Esta elección es reproducible: volver a correr
`python src/compare_prompt_techniques.py` regenera la comparación con el
set de prueba y las variantes de prompt actuales, agregando filas nuevas a
`metrics/prompt_comparison.csv` en vez de sobreescribir la evidencia.

## Métricas de ejemplo (corridas reales de producción, `gpt-4o-mini`)

Capturadas de `metrics/metrics.csv` (usando el prompt final de
chain-of-thought, `prompts/main_prompt.txt` — sin ejemplos resueltos, solo
la instrucción de pensar paso a paso, por eso acá `tokens_prompt` es más
bajo que en la variante few-shot probada en la comparación de arriba):

| pregunta | tokens_prompt | tokens_completion | latency_ms | estimated_cost_usd | valid_json | repaired |
|---|---|---|---|---|---|---|
| "No puedo acceder a mi cuenta..." | 462 | 132 | 2189.5 | $0.0001485 | True | False |
| "che quiero cancelar" | 442 | 82 | 1640.6 | $0.0001155 | True | False |

Ambas corridas produjeron JSON válido según el contrato en el primer
intento (no hizo falta reparación, `repaired=False`).

## Trade-offs

- **Set de prueba chico para la comparación de técnicas.** 5 preguntas por
  variante alcanzan para exponer la diferencia de costo, pero no para
  separar estadísticamente la precisión entre técnicas (las tres dieron
  100%). Una decisión de producción querría un set etiquetado más grande
  (un criterio habitual para este tipo de evaluación es del orden de
  cientos de ejemplos) antes de confiar del todo en los números de
  precisión; acá
  se acotó a propósito para mantener bajo el gasto de API y el tiempo del
  ejercicio, sin dejar de ser una comparación real y reproducible en vez
  de un supuesto.
- **`response_format=json_object` + un intento de reparación vs. desvío del
  esquema.** Forzar el modo JSON garantiza validez sintáctica pero no
  validez de negocio (el modelo igual podría omitir un campo o inventar
  una acción fuera del catálogo). `schema.py` valida el contrato como un
  paso separado del parseo de JSON, y sigue existiendo el camino de
  `fallback_response` para el caso en que ni siquiera la reparación
  produzca un contrato válido.
- **Tabla de precios estática.** `estimate_cost_usd` usa precios
  hardcodeados por modelo en vez de consultar una API de pricing, porque
  OpenAI no expone una; es un riesgo de desactualización ya documentado en
  el README.
- **Todavía no hay capa de seguridad/moderación.** El objetivo bonus
  (`src/safety.py`) se pospuso deliberadamente para mantener esta primera
  iteración enfocada en el flujo obligatorio (contrato JSON + métricas +
  técnica de prompting + test) funcionando de punta a punta antes de sumar
  una segunda capa de defensa. Un enfoque de defensa en profundidad
  (sanitización de entrada, compuerta de salida, un contrato de
  moderación con su propio esquema JSON) es el patrón de referencia
  estándar para implementarlo.

## Próximos pasos

- Agregar `src/safety.py`: una capa de moderación/fallback para entradas
  adversariales (intentos de prompt injection dentro de la "pregunta"),
  siguiendo un patrón de defensa en profundidad — sanitización de
  entrada, una compuerta de salida, y un contrato de moderación
  (`action`, `reasons`, `severity`) logueado aparte de las métricas de
  negocio.
- Ampliar el set de prueba en `src/compare_prompt_techniques.py` más allá
  de 5 preguntas por variante, para tener una comparación de precisión
  estadísticamente significativa y no solo una comparación de costo.
- Evaluar cacheo del prompt de sistema una vez que se estabilice, para
  reducir el costo fijo por llamada mencionado arriba.
