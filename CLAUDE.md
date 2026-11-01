# Contexto — Proyectos Integradores, carrera AI Engineering (Henry)

Este repo (`AI-Engineering`) es el destino de **todas** las entregas de la carrera, módulo a módulo (Módulo 1, 2, 3, 4...), no solo la actual. Las secciones de "Reglas transversales" abajo aplican a todos los módulos; el resto del documento describe cada módulo por separado y se va ampliando a medida que avanzan.

## Reglas transversales (todos los módulos)

**Estructura de repo (decisión 2026-09-25, aplica a toda la carrera):** monorepo simétrico — cada módulo vive en su propia carpeta top-level y autocontenida (`modulo-1/`, `modulo-2/`, ...), con su propio `src/`, `README.md`, `requirements.txt` y `.env.example`. El `README.md` de la raíz es solo un índice que linkea a cada módulo. Un `.venv` y un `.env` compartidos en la raíz sirven para todos los módulos (cada script carga el `.env` con `load_dotenv()` sin ruta explícita, que busca hacia arriba en los directorios padres — así no hace falta duplicar secretos por módulo). El Módulo 1, entregado originalmente plano en la raíz y ya validado por Henry, se movió a `modulo-1/` para adoptar este patrón antes de empezar el Módulo 2 (sin cambios funcionales — ver commit `chore: mover proyecto integrador del Modulo 1 a modulo-1/`).

**Framing de negocio preferido (decisión 2026-09-11, aplica a toda la carrera):** cuando la consigna de un módulo deja espacio de elección (ejemplos, dominio de datos, vocabulario, tipo de acciones/casos de uso), inclinarse por defecto hacia un dominio de **Help Desk / soporte al cliente vía tickets**, que además es coherente con el contexto de negocio de la consigna del Módulo 1. **La consigna de cada módulo manda siempre por encima de este framing** — si en algún punto entran en conflicto, gana la consigna. (El Módulo 2 no entra en conflicto: su consigna ya trae un dominio propio —FAQs de una empresa de HR SaaS— que es primo cercano del framing de Help Desk, así que no hizo falta invocar esta regla de default.)

**Branching (decisión 2026-09-11, aplica a toda la carrera):** `develop` + feature branches cortas, siguiendo la skill `git-workflow-and-versioning`. Nunca commitear directo a `main`.
1. Cada objetivo/módulo va en su propia rama corta (`feature/...` o `chore/...`) que mergea a `develop`.
2. `main` se actualiza solo con un merge deliberado y explícitamente pedido desde `develop`.

## Qué es este workspace

La raíz del workspace es esta carpeta (`AI-Engineering`, mi repo). El material externo vive **adentro** de `material/`, que está en `.gitignore` (no se versiona). Estructura real (actualizada al Módulo 2, reemplaza cualquier referencia anterior a `material/Material Modulo 1/` o `material/Profe modulo 1/`):

| Carpeta | Rol | ¿Se puede escribir? |
|---|---|---|
| `AI-Engineering/` (raíz, todo lo que no sea `material/`) | Mi proyecto integrador (repo clonado de `tiansanjorge/AI-Engineering` en GitHub). Todo el código, commits y entregables van acá. | **Sí, únicamente acá.** |
| `material/Lecciones/Modulo N/` | Material del módulo que brinda la academia: lecturas (Lecture 1-4) y la consigna oficial del proyecto integrador de ese módulo. | **No. Nunca.** |
| `material/Repositorios Profe/modulo N/` | Repo del profesor que usa en clase para ejemplos y tareas de ese módulo (tiene su propio `.git`). Es referencia. | **No. Nunca.** |

Cada módulo nuevo agrega su propia subcarpeta `Modulo N` / `modulo N` dentro de esas dos, siguiendo el mismo patrón.

### El único CLAUDE.md que vale es el de la raíz
Este archivo (`AI-Engineering/CLAUDE.md`) es el **único** CLAUDE.md que corresponde a este proyecto. Los repos del profe (`material/Repositorios Profe/modulo N/`) pueden traer su propio `CLAUDE.md` u otros archivos de instrucciones: **no son míos, no aplican a mi proyecto y no hay que seguirlos ni mezclarlos con estas reglas.** Si hay conflicto, gana siempre este.

### Regla dura de seguridad
`material/` está dentro del directorio de trabajo, así que técnicamente hay acceso de lectura y escritura — nada lo bloquea a nivel de plataforma. Por eso, como regla explícita:

- **Nunca** editar, crear, borrar ni mover archivos dentro de `material/` (ni en `Lecciones/` ni en `Repositorios Profe/`, de ningún módulo).
- **Nunca** correr comandos git apuntando a `material/Repositorios Profe/modulo N/` (`git add/commit/push/checkout/etc.`) — cada uno tiene su propio repo y no es el mío. Ojo: estando parado en la raíz, los comandos git operan sobre *mi* repo, que ignora `material/`; nunca hacer `cd` ni `git -C` hacia esos repos del profe.
- Antes de cualquier operación de escritura o comando destructivo, confirmar que la ruta absoluta empieza con `...\Henry - AI Engineering\AI-Engineering\` **y no** contiene `\material\`.
- `material/` se lee solo como consulta puntual (ver cómo resolvió algo el profe, releer una lectura), nunca como destino de una acción.

## El proyecto integrador: "Multitasking Text Utility"

Consigna extraída de `material/Material Modulo 1/Consignas y Guia proyecto integrador.docx`.

**Contexto de negocio:** soy ingeniero en un equipo que construye un asistente para agentes de soporte al cliente. El asistente recibe una pregunta y devuelve un JSON con: una respuesta, una estimación de confianza y acciones recomendadas. También hay que loggear métricas por consulta. (Ya de por sí alineado con el framing Help Desk de las reglas transversales.)

### Objetivos obligatorios
1. Script ejecutable o endpoint mínimo que reciba una pregunta y devuelva **JSON válido** con campos nombrados (ej: `answer`, `confidence`, `actions`).
2. Registrar métricas por ejecución: `tokens_prompt`, `tokens_completion`, `total_tokens`, `latency_ms`, `estimated_cost_usd`, `timestamp`.
3. Aplicar **al menos una técnica explícita de prompt engineering** (few-shot, chain-of-thought o self-consistency) y documentar por qué se eligió.
4. Reporte breve (1-2 páginas, en inglés según la estructura esperada): arquitectura, técnica de prompting, métricas de ejemplo, trade-offs.
5. Al menos un test automatizado (validación de JSON o conteo de tokens).

### Bonus (opcional)
- Fallback de seguridad/moderación para entradas adversariales (`src/safety.py`), documentado con un ejemplo concreto de ataque y cómo lo manejó el sistema. Defensa en capas, no una sola línea de defensa.

### Estructura de repo esperada (checklist de entregables)

```
AI-Engineering/
├── src/run_query.py        # o app/endpoint.py — acepta pregunta, llama a OpenAI, devuelve JSON válido
│   └── safety.py           # bonus: moderación/fallback
├── prompts/main_prompt.txt # prompt con few-shot / instrucciones de esquema JSON
├── metrics/metrics.csv     # o metrics.json — una fila por ejecución
├── reports/PI_report_en.md # 1-2 páginas: arquitectura, prompting, métricas, desafíos
├── tests/test_core.py      # al menos 1 test
├── README.md               # setup, env vars, comandos, cómo reproducir métricas, limitaciones
└── .env.example
```

### Requisitos de entrega
- Repo público en Git, autocontenido, ejecutable sin dependencias externas no documentadas.
- Credenciales solo por variable de entorno (`OPENAI_API_KEY`), nunca hardcodeadas.
- README y reporte consistentes entre sí.
- Al menos una ejecución registrada que produzca JSON + métricas.
- Si se usó IA como apoyo para programar: documentar qué prompts se usaron y cómo influyeron en decisiones técnicas (el objetivo es demostrar comprensión propia, no delegarla).

### Criterios que se valoran (guía del profesor)
- Que funcione de punta a punta, no cantidad de features.
- Código legible, modular, responsabilidades separadas.
- Decisiones de prompting y diseño documentadas y justificadas (tratar el prompt como hipótesis: probar, iterar, dejar evidencia).
- Salida validada, no asumida — pensar qué pasa si el modelo rompe el contrato JSON.
- Métricas persistidas y auditables, no solo en consola.
- Commits chicos y descriptivos desde el inicio.

## Estado actual del proyecto (Módulo 1 validado por Henry, actualizado 2026-09-20)

- Repo git con remote `origin` en `git@github.com:tiansanjorge/AI-Engineering.git`. Ramas `main` y `develop` activas, flujo de branching transversal en uso (ver arriba) — `main` ya recibió el merge de `develop` de la entrega del Módulo 1 (validada por Henry).
- Objetivos obligatorios: **todos cumplidos**, en la estructura de carpetas esperada.
  - `src/run_query.py` — entrypoint CLI, pregunta → JSON validado.
  - `src/llm_client.py`, `schema.py`, `metrics.py`, `safety.py` — capas de soporte (llamada a OpenAI + reparación de JSON, validación de contrato, métricas/costo, seguridad).
  - `src/compare_prompt_techniques.py` — técnica de prompting (chain-of-thought) elegida con un experimento real y reproducible (evidencia medida, no a ojo). Historia completa (3 rondas, con un hallazgo real que llevó a ajustar el prompt) en `reports/PI_report_en.md`.
  - `prompts/main_prompt.txt` + `prompts/variants/` — prompt de producción + variantes comparadas.
  - `metrics/metrics.csv` + `metrics/prompt_comparison.csv` — ejecuciones reales registradas.
  - `reports/PI_report_en.md` (oficial) + `PI_report_es.md` (traducción para consulta propia) — reportes cortos. El uso de IA y del material de referencia de `material/` se declara en el README (sección "Sobre el uso de IA como apoyo").
  - `tests/test_core.py` — 32 tests unitarios y `tests/test_integration.py` — 7 tests de integración de `run_query.run()` con OpenAI mockeado. Ninguno llama a la API.
  - `README.md` — setup, uso, estructura, limitaciones conocidas.
- **Bonus implementado**: `src/safety.py` con defensa en capas (entrada + salida) ante prompt injection, catálogo de patrones por categoría medido contra un corpus etiquetado.
- El MVP exploratorio inicial (`index.py`, `testing.py`) ya se borró — quedó completamente reemplazado por la estructura de arriba.
- El flujo de trabajo usado: ramas `feature/...` cortas → code review (`/code-review`) → merge a `develop`. Ver historial de `develop` para el detalle de cada entrega.

## Módulo 2: chatbot de FAQs con RAG

Consigna extraída de `material/Lecciones/Modulo 2/Consignas y guía proyecto integrador.docx`. Vive en `modulo-2/` (ver regla transversal de estructura de repo).

**Contexto de negocio:** soy ingeniero de IA en una empresa de HR SaaS. Soporte recibe +200 preguntas repetitivas por día sobre políticas y funcionalidades ya documentadas. El objetivo es un chatbot de FAQs basado en RAG que responda al instante recuperando información real de la documentación, en vez de que el modelo responda de memoria (que es justo lo que M1 no resolvía — ver framing arriba).

### Objetivos obligatorios
1. Pipeline de indexación (`src/build_index.py`): carga un documento de texto plano (`data/faq_document.txt`, ≥1000 palabras), lo divide en **≥20 chunks** (50-500 tokens cada uno), genera embeddings y los guarda junto con el texto de cada chunk.
2. Pipeline de consulta (`src/query.py`): pregunta del usuario → embedding → búsqueda vectorial (k-NN/ANN/rango/híbrida, con la similitud calculada explícitamente) → recupera 2-5 chunks relevantes → genera respuesta con un LLM → devuelve JSON con **exactamente** `user_question`, `system_answer`, `chunks_related`.
3. `outputs/sample_queries.json`: ≥3 ejemplos de punta a punta.
4. `README.md` propio (setup, uso, estructura, justificación de chunking y método de búsqueda) y `.env.example`.

### Bonus (opcional, después del flujo obligatorio)
- Agente evaluador: recibe `user_question` + `system_answer` + `chunks_related`, devuelve `{"score": 0-10, "reason": "..."}` evaluando ≥2 dimensiones (relevancia de chunks, fidelidad de la respuesta al contexto, completitud).

### Decisiones tomadas (2026-09-25)
- **Proveedor:** solo OpenAI (`text-embedding-3-small` para embeddings), igual que M1. No se replica el soporte dual OpenAI/Gemini del repo del profe.
- **Vector store:** archivo local (JSON) + búsqueda k-NN a mano con NumPy, similitud coseno explícita — no ChromaDB. Motivo: la rúbrica pide mostrar el cálculo de similitud explícitamente, lo cual es más directo de auditar a mano que dentro de una librería; y la migración a un vector store real (si M3 lo exige) es directa después, sin rehacer chunking/embeddings/prompt.
- **Chunking:** tamaño fijo con solapamiento (150 tokens por chunk medidos con `tiktoken`/`cl100k_base`, 30 de overlap, ~20%; originalmente 100/20 en palabras, migrado a tokens el 2026-09-28 para alinearse con la unidad de la consigna). Motivo: son los parámetros que la rúbrica pide documentar explícitamente (`chunk_size`, `overlap`), el repo del profe midió que en documentos chicos esta estrategia empata con las "avanzadas" (semántica, por estructura), y el overlap mitiga el riesgo de cortar una oración importante a la mitad.
- **Agente evaluador (bonus):** se encara después de que el flujo obligatorio funcione de punta a punta, mismo criterio que en M1 (camino principal primero, iterar después).
- **Documento fuente:** contenido original a escribir (no se copia de `material/Repositorios Profe/modulo 2/datos/`, que es solo referencia de qué tipo de contenido usar).

### Estado actual (actualizado 2026-09-28)
Flujo obligatorio completo y funcionando de punta a punta, ya mergeado a `develop` (incluye la migración de chunking a tokens del 2026-09-28):
- `data/faq_document.txt` — documento original (1747 palabras, 13 secciones) sobre NimbusHR (HR SaaS ficticio).
- `src/chunking.py`, `embeddings.py`, `vector_store.py`, `build_index.py` — pipeline de indexación (chunk_size=150, overlap=30 en tokens → 23 chunks reales, 57-150 tokens c/u). Corrido contra la API real, índice guardado en `data/index.json`.
- `src/llm_client.py`, `query.py` — pipeline de consulta (k-NN con coseno explícito → contexto → generación). JSON de salida con las 3 claves exactas que pide la consigna.
- `outputs/sample_queries.json` — 3 preguntas reales (dato puntual, sí/no, "cómo hacer"), corridas dos veces: la primera corrida encontró un hallazgo real (el modelo rechazaba una pregunta cuyo chunk recuperado sí tenía la respuesta, por ser demasiado literal con la regla "si no está, decilo"); se ajustó la regla del prompt a "rechazá solo si ningún fragmento se relaciona" y las 3 preguntas pasaron a responder bien. Detalle completo en `modulo-2/README.md`.
- `tests/test_core.py` — 14 tests (chunking, similitud coseno, k-NN, guardado/lectura del índice, contrato JSON de `query.py`), ninguno llama a la API real.
- `README.md` propio con setup, uso, estructura, decisiones técnicas justificadas y el hallazgo documentado.
- **Bonus implementado:** `src/evaluator.py` + `src/evaluate_samples.py`. Puntúa (0-10 + reason) cada entrada de `outputs/sample_queries.json` en 3 dimensiones (relevancia, fidelidad, completitud) y guarda el resultado en `outputs/sample_queries_evaluated.json` — separado, sin tocar el contrato de 3 claves de `sample_queries.json`. Hallazgo real: la primera versión del evaluador acertaba el score pero su `reason` afirmó que faltaba un dato que en realidad estaba en el texto evaluado (error de lectura del propio LLM-juez); se corrigió exigiendo cita textual entre comillas para cada observación. Limitación conocida documentada en el README: un LLM-juez da una señal aproximada, no una verificación formal. 16 tests en total (14 del flujo obligatorio + 2 del evaluador, mockeado).

### Feedback recibido del Módulo 2 (2026-10-09)
Módulo 2 **validado**, con feedback muy positivo (RAG funcional, trazabilidad vía `chunks_related`, tests, hallazgo real documentado, evaluador bonus). **Decisión: no se aplican fixes al Módulo 2**; las mejoras se tienen en cuenta al diseñar el Módulo 3:
1. **Evaluación con más cobertura:** el M2 solo tiene 3 preguntas end-to-end y evaluadas. En M3 armar un set más amplio y sistemático (la consigna ya pide ≥10 test queries con categoría esperada; incluir casos borde, ambiguos y fuera de dominio) y reportar resultados agregados (p. ej. accuracy de routing).
2. **Chunking más robusto:** el chunking fijo por tokens puede cortar oraciones. En M3 considerar chunking por estructura (secciones/encabezados) o por límites de oración, manteniendo overlap, y justificar la elección.
3. **Metadatos y filtros de recuperación:** guardar metadatos por chunk (dominio, sección, fuente) y evaluar filtros de recuperación; encaja de forma natural con 3 corpus separados.
4. **Diversidad de documentos:** M3 exige 3 colecciones (`hr_docs/`, `tech_docs/`, `finance_docs/`, ≥50 chunks c/u); usarlas con documentos variados, no un solo archivo por dominio.
5. **Búsqueda por fuerza bruta:** adecuada para el corpus chico, pero no escala. M3 usa FAISS (según las lecciones); dejar documentada la limitación/migración, no es prioridad.

## Módulo 3: sistema multi-agente con LangChain + Langfuse

Consigna extraída de `material/Lecciones/modulo 3/Consignas y guía proyecto integrador.docx`. Vive en `modulo-3/`.

**Contexto de negocio:** AI engineer en una SaaS mediana; los tickets se enrutan mal entre áreas (HR, IT, Finance, Legal). Se pide un orquestador que clasifique la intención y rutee de forma condicional a agentes RAG especializados (≥3, colecciones `data/hr_docs/`, `tech_docs/`, `finance_docs/` con ≥50 chunks c/u), todo con LangChain y trazado completo en Langfuse. Entregables: notebook `multi_agent_system.ipynb` (6 secciones: setup, docs/vector stores, agentes, orquestador y routing, pruebas, Langfuse) o archivos en `src/agents/`; `test_queries` (≥10, con intent esperado, incluye casos borde); README; `requirements.txt` (≥9 paquetes); `.env.example`. **Bonus:** agente evaluador con la Score API de Langfuse (1-10 por respuesta).

### Decisiones tomadas (2026-10-09)
- **Stack:** LangChain 1.x + LangGraph (orquestador con aristas condicionales) + **Chroma persistente** (no FAISS: filtros por metadatos nativos, camino a `HttpClient` en el M4) + Langfuse Cloud (región **EE.UU.**, `us.cloud.langfuse.com`) + Pydantic. `pip` + `requirements.txt` (como M1/M2).
- **Modelos:** `gpt-4o-mini` / `text-embedding-3-small`, configurables por `CHAT_MODEL`/`EMBEDDING_MODEL`. Los nombres GPT-6 del repo del profe no están verificados en mi cuenta.
- **Dominios:** HR, Tech/IT y Finance como agentes; Legal es caso borde (fuera de alcance). Un solo agente por consulta en el MVP (multi-intención = stretch).
- **Forma:** módulos en `modulo-3/src/` + notebook que los importa; una función de entrada única tipada (pensando en envolverla con FastAPI en el M4). Índices Chroma en `modulo-3/chroma_db/` (gitignoreado, se reconstruyen desde los documentos).
- **Evaluador (fase 7):** lo etiqueta/calibra Claude, no el usuario. El usuario aprende con la guía final (`guias/modulo-3-guia.md`), no fase a fase.
- **Autorización:** commits y manejo de ramas (feature → `develop`) delegados a Claude; nunca `main`.

### Hallazgos de la auditoría del material (importantes)
- Las lecturas usan APIs **obsoletas**: Langfuse v2 (`langfuse.trace()`, `trace.span()`, `langfuse.score()`) y LangChain legacy (`initialize_agent`, `RetrievalQA`). Usar Langfuse v4 (`get_client()`, `start_as_current_observation`, `propagate_attributes`, `langfuse.langchain.CallbackHandler`, `create_score`) y LangChain 1.x.
- `client.api.trace.get()` devuelve **410** en organizaciones nuevas (≥2026-09-16): leer traces con `client.api.observations.get_many(trace_id=...)`.
- El repo del profe (`henry-ai-engineering`) no usa Langfuse (apaga el tracing); sirve de referencia para LangGraph (`graph.py`: router + `Send` + especialistas + abstención; `operations.py`: golden set y métricas; clase 5: supervisor/handoff; clase 6: juez calibrado).

### Plan por fases (cada fase: tests/verificación → commits chicos → actualizar este estado)
0 Setup (hecho) · 1 Corpus (3 dominios, 1a/1b/1c) · 2 Ingesta + Chroma (chunking por estructura, metadatos) · 3 Agentes RAG · 4 Orquestador LangGraph · 5 Langfuse · 6 Golden set (~30) + evaluación agregada + iteración v1→v2 · 7 Bonus evaluador · 8 Notebook, README, guía, corrida limpia, `/code-review`, merge.

### Estado actual
- **Fase 8 completada (entrega):** `modulo-3/multi_agent_system.ipynb` (8 secciones: setup, documentos y vector stores, agentes, orquestador, pruebas, Langfuse, bonus evaluador, historial; ejecutado, con salidas, sin secretos; se genera con `scripts/build_notebook.py [--execute]`, fijando `LANGFUSE_TIMEOUT=30`), `modulo-3/README.md`, fila en el README de la raíz, `guias/modulo-3-guia.md` (gitignorada) y declaración de uso de IA. Verificado desde cero en un clon limpio con venv nuevo (instalación, índice, 112 tests (hoy 114) y notebook completo; ojo: `venv` falla si la ruta es muy larga en Windows). **`modulo-3/PENDIENTES.md`: registro de 30 problemas conocidos y mejoras con evidencia** (el usuario pidió anotar lo que no se resuelve y revisarlo al terminar; mantenerlo actualizado). `/code-review` de la rama: arreglados los fallos de API sin capturar en recuperación y guarda (P-30, 114 tests); el resto (texto sin respaldo en abstención P-24, reconstrucción destructiva del índice P-25, ingesta frágil P-26, etc.) quedó registrado. Rama `feature/modulo-3-entrega`.
- **Fase 7 completada (bonus):** `src/evaluator.py` (juez con **verificación estructurada**: el LLM descompone la consulta en partes, contrasta cada afirmación de la respuesta con una cita literal de los fragmentos (marcando la central) y decide si una abstención era justificada; el puntaje 1-10 + relevancia/completitud/exactitud se **calcula en código** con reglas explícitas; recibe los fragmentos con los que contaba el agente, marcando los citados). Score API de Langfuse: `quality`, `quality_relevance`, `quality_completeness`, `quality_accuracy` (+ `quality_evaluator_failed` si el juez falla); la llamada del juez queda en el mismo trace. `scripts/calibrate_judge.py` + `eval/judge_calibration.json` (30 ítems con puntajes humanos escritos y commiteados ANTES de correr el juez; split tune/test; historial en `eval/judge_calibration_history.csv`): **j3 + gpt-4o → Spearman 0,88, error medio 0,87, 0 falsos buenos, 93 % de acuerdo bueno/malo** (gpt-4o-mini con el mismo método: 3 falsos buenos → el juez usa `JUDGE_MODEL=gpt-4o`, ~USD 0,0055 por respuesta). `run_golden.py --judge`: golden dev v5 → media 9,06, 5 respuestas < 7. **Hallazgo real:** una inyección en la consulta (A-03) contamina `also_involves` del router (8/8) y el usuario recibe una nota de derivación equivocada; ni el prompt ni un filtro por distancia lo arreglan (las notas legítimas se solapan en distancia) → **limitación conocida**, chequeo agregado al golden (dev 97 %). 112 tests sin API. Detalle en `modulo-3/eval/README.md` (sección Fase 7).
- **Fase 6 completada:** `test_queries.json` (dev, 39 casos), `test_queries_holdout.json` (14), `test_queries_blind.json` (14); `src/evaluation.py` (métricas determinísticas: ruteo strict/lenient, estado, hechos, fuentes, frases prohibidas, abstenciones/respuestas indebidas, matriz de confusión, latencia, costo) y `scripts/run_golden.py --run-tag X --set dev|holdout|blind` (traza cada caso en Langfuse con tags y score `case_passed`; escribe `eval/golden_runs/*.json` y `eval/golden_summary.csv`). **Iteración documentada en `modulo-3/eval/README.md`:** v1 92 % dev / 79 % holdout → v2 router con alcance explícito (97 % / 100 %) → v3 glosario de «reembolso» en Finanzas → set ciego: 86 % + bug `KeyError` (`also_involves` con `out_of_scope`) → v4 `src/routing_guard.py` (si el router dice `out_of_scope` pero algún dominio tiene un chunk a distancia coseno < 0,43, se rutea ahí) → v5 abstención decidida por evidencia (≥ 1 fuente válida) en vez del booleano `abstained` autodeclarado (T-FI-05: 6/10 → 0/10 abstenciones) → **100 % en dev, holdout y blind, repetido dos veces**. Limitaciones declaradas: sets chicos, ninguno virgen tras v4, no determinismo del modelo. 90 tests sin API.
- **Fase 5 completada:** `src/observability.py` → `traced_query(question, user_id, session_id, tags, metadata, expected_intent)`: span raíz `support-request` + `propagate_attributes` (user/session/tags/metadata) + `CallbackHandler` de Langfuse (spans de LangGraph/LangChain: `LangGraph` → `route` → `orchestrator-routing` → `ChatOpenAI`; `<dominio>` → `<dominio>-agent` → `retriever_<dominio>` + `ChatOpenAI`); errores marcados `level=ERROR` en el trace y re-lanzados; scores `routed_intent` (CATEGORICAL, intención ruteada) y `routing_correct` (BOOLEAN, si hay `expected_intent`). `scripts/verify_tracing.py` verifica contra Langfuse real el checklist de 6 puntos de la lecture 4 en 3 consultas (hr, tech, out_of_scope): **todas OK** (evidencia en `outputs/tracing_check.json`, con URLs de los traces). `scripts/ask.py --trace`. 64 tests sin red (cliente Langfuse simulado).
  - **Hallazgos de API (organización creada ≥ 2026-09-16):** `api.trace.get` y `api.scores.get_many` devuelven **410** → leer con `api.observations.get_many(trace_id=..., fields="core,basic,io,usage,time")` y `api.scores_v3.get_many_v3(trace_id=...)`. No existe `update_current_trace` en v4: lo conocido de antemano va en `propagate_attributes`; lo descubierto después (intención ruteada) va como score. Los spans internos de LangChain (`ChatPromptTemplate`, `RunnableLambda`, `RunnableSequence`, `choose_branch`) agregan ruido: aceptable, se filtra por nombre en la UI.
- **Fase 4 completada:** `src/agents/orchestrator.py` (router LCEL con salida estructurada `RouteDecision{intent, confidence, reason, also_involves}`, prompt con categorías, criterios de desempate y ejemplos; grafo LangGraph `route → {hr|tech|finance → finalize | out_of_scope | escalate}` con aristas condicionales; si el router falla o devuelve una categoría inválida se **escala a una persona** en vez de rutear al azar; `also_involves` agrega una nota al usuario; `low_confidence` < 0,6 queda marcado; entrada validada: vacía o > 2000 caracteres → `ValueError` sin llamar al modelo) y `src/multi_agent_system.py` (`answer_query(question, config=None)`: entrada única del sistema, pensada para envolverse con FastAPI en el M4). Spans con nombre: `orchestrator-routing`, nodos del grafo, `<dominio>-agent`. `scripts/ask.py`, `scripts/sample_orchestrator_runs.py` → `outputs/orchestrator_samples.json`: **ruteo 10/10** en una prueba de humo (incluye frontera «no puedo entrar a Nimbus Expenses» → tech + nota de Finanzas, legal/general/inyección → out_of_scope, y una consulta con errores de ortografía). 57 tests sin API.
  - **Hallazgo abierto para la Fase 6 (caso v1):** «¿Cuántos días tengo para pedir el reembolso de un viaje?» → ruteo correcto a finance, el retrieval SÍ trajo el chunk «Plazo para presentar gastos» (puesto 2 de 4, tras «Reembolsos a clientes»), pero el agente se abstuvo. Falla de **generación**, no de recuperación. Candidatos de fix a medir: ajuste del prompt del agente, `k` mayor, reordenar/filtrar por metadatos.
- **Fase 3 completada:** `src/agents/rag_agent.py` (agente RAG genérico: retriever de su colección → prompt con reglas M2 «abstenerse solo si NINGÚN fragmento se relaciona» → salida estructurada `LLMAnswer` → `AgentResult` con fuentes verificadas contra lo recuperado, ids inventados descartados, abstención ante fallo del modelo o sin fuentes válidas; expuesto como `Runnable` nombrado `<dominio>-agent` para anidar spans en Langfuse), `hr_agent.py`, `tech_agent.py`, `finance_agent.py` (configuración fina + nota de fronteras), `registry.build_agents()`. El retriever ahora es `ScoredChromaRetriever` (BaseRetriever que agrega la distancia coseno a cada chunk). `scripts/run_agent.py` y `scripts/sample_agent_runs.py` → `outputs/agent_samples.json` (9 corridas reales: normales, frontera, fuera de dominio, inyección; todas correctas). 38 tests sin API (LLM simulado en `tests/conftest.py`).
- **Fase 2 completada:** `src/config.py`, `src/ingestion.py` (chunking por estructura: sección `##` / fila CSV / párrafo `.txt` = 1 chunk; tope 300 tokens con corte por oraciones y solapamiento de 1 oración; metadatos `chunk_id, domain, source, doc_title, section, format, part, tokens`), `src/vector_store.py` (una colección Chroma persistente por dominio, similitud coseno, ids deterministas, reconstrucción idempotente, retriever con filtro por metadatos). `scripts/build_index.py` (96 HR / 97 Tech / 95 Finance chunks, ~USD 0,0005) y `scripts/eval_retrieval.py` con `eval/retrieval_cases.json` (18 preguntas parafraseadas): **hit@4 = 100 %, hit@1 = 89 %, MRR = 0,92**; el ruteo ingenuo por mejor score de retrieval da 100 % en estas preguntas limpias (el orquestador tiene que demostrar valor en ambiguas y fuera de dominio). 27 tests sin API (embeddings falsos deterministas). Resultados en `eval/retrieval_results.json`. Lint: `ruff check modulo-3` (el entorno aplica reglas extra además de las default).
- **Fase 1 completada:** corpus original de Nimbus Desk (SaaS de help desk ficticia) en `modulo-3/data/{hr,tech,finance}_docs/`: 6 documentos por dominio (4 `.md` por secciones, 1 `.csv`, 1 `.txt`), ~95 unidades c/u (28-126 tokens). Fronteras entre dominios documentadas en `data/README.md` (casos difíciles para el golden set). `scripts/corpus_stats.py` valida unidades/tokens y la forma de los CSV. **Nota para la Fase 2:** las unidades son cortas (~80 tokens), por lo que el chunking por estructura debe ser 1 sección = 1 chunk (agrupar secciones bajaría de 50 chunks por dominio).
- **Fase 0 completada:** estructura `modulo-3/`, `requirements.txt` pinneado, `.env.example`, `scripts/smoke_test.py` (Langfuse auth, Chroma + filtro, LangGraph, traza LLM leída de vuelta) pasando contra servicios reales.

## Módulo 4: agente de comparación de contratos (visión + 2 agentes + Langfuse)

Consigna: `material/Lecciones/Modulo 4/Consignas del proyecto final.docx`. Vive en `modulo-4/`. **Es el proyecto final y se evalúa con defensa oral en vivo (30 min, 1 a 1)**: por eso el código lleva comentarios conceptuales breves y se mantiene `guias/modulo-4-guia.md` (gitignorada; parte A = cómo funciona, parte B = decisiones técnicas + preguntas probables del corrector; es un solo documento).

**Negocio:** LegalMove (ficticia); Compliance tarda 40+ h/semana comparando contratos con sus adendas. Entrada: 2 imágenes (original + adenda) → JSON `ContractChangeOutput` {sections_changed, topics_touched, summary_of_the_change}, validado con Pydantic y trazado en Langfuse.

### Decisiones (2026-11-01)
- **Modelos:** `gpt-4o` para visión y agentes (la consigna lo pide), configurable (`VISION_MODEL`, `AGENT_MODEL`). Idioma: español.
- **Langfuse:** proyecto NUEVO y separado del M3 (claves en el `.env` compartido de la raíz; los scripts del M3 ahora apuntarían al proyecto del M4). Skill `langfuse` instalado globalmente (se usó en la fase 6; docs primero).
- **Contratos de prueba:** generados por script (`scripts/generate_contracts.py`, Pillow) con ground truth (`expected.json`): par1 simple, par2 complejo, par3 = par1 como escaneo degradado nivel 3/5. Empresas ficticias.
- **Dos modelos Pydantic a propósito:** `ExtractionResult` (interno, con tipo de cada cambio) del que se DERIVA `ContractChangeOutput` por código (no se le pide al LLM).

### Estado actual
- **Fases 1-6 completadas** (ramas `feature/modulo-4-*` mergeadas a `develop`; la de la fase 6 es `feature/modulo-4-main-langfuse`). Pendiente: fase 7 (evaluación de punta a punta + iteración de prompts documentada), fase 8 (README con diagrama, guía, `/code-review`, merge).
- `src/`: `config.py`, `errors.py`, `models.py`, `llm.py`, `image_parser.py` (validación local → base64 → GPT-4o `detail=high`; guarda contra negativas), `agents/{contextualization,extraction}_agent.py` (structured output estricto + auto-reparación con el error de Pydantic), `observability.py` (spans por etapa, `TokenTracker`), `main.py` (CLI + `analyze_contracts` con dependencias inyectables), `text_metrics.py` (WER).
- **Medido:** parsing WER 0,000 en pares limpios, 0,017-0,029 en el par 3; agentes 7/7 secciones, tipos correctos, 0 falsos positivos; traza real 40/40 chequeos (`scripts/verify_tracing.py`); ~13 s y ~7-8 mil tokens por análisis. 50 tests sin API.
- **`modulo-4/PENDIENTES.md`** (mantener actualizado): P-04 y P-06 (alucinación y errores de dígitos con escaneos malos; mitigado en parte por el agente 1, que cruza fechas y avisa), P-07 (privacidad en Langfuse Cloud), P-02/03/08/09.

## Cómo trabajar conmigo en este proyecto

- Priorizar el flujo principal (una llamada que devuelva JSON útil) antes de pulir, iterar el prompt como si fuera código, y armar la estructura de carpetas esperada desde el principio para no migrar después.
- Seguir las reglas globales de `~/.claude/CLAUDE.md` (conventional commits, castellano rioplatense, no hacer build sin pedirlo, plan antes de tocar +2 archivos, etc.) y las reglas transversales de este archivo (branching y framing, ver arriba).
