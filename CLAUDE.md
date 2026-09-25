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
- **Chunking:** tamaño fijo con solapamiento (~100 palabras por chunk, ~20% de overlap). Motivo: son los parámetros que la rúbrica pide documentar explícitamente (`chunk_size`, `overlap`), el repo del profe midió que en documentos chicos esta estrategia empata con las "avanzadas" (semántica, por estructura), y el overlap mitiga el riesgo de cortar una oración importante a la mitad.
- **Agente evaluador (bonus):** se encara después de que el flujo obligatorio funcione de punta a punta, mismo criterio que en M1 (camino principal primero, iterar después).
- **Documento fuente:** contenido original a escribir (no se copia de `material/Repositorios Profe/modulo 2/datos/`, que es solo referencia de qué tipo de contenido usar).

### Estado actual (actualizado 2026-09-25)
Flujo obligatorio completo y funcionando de punta a punta, en `feature/modulo-2-rag-faq` (todavía no mergeada a `develop`):
- `data/faq_document.txt` — documento original (1747 palabras, 13 secciones) sobre NimbusHR (HR SaaS ficticio).
- `src/chunking.py`, `embeddings.py`, `vector_store.py`, `build_index.py` — pipeline de indexación (chunk_size=100, overlap=20 → 22 chunks reales, 67-100 palabras c/u). Corrido contra la API real, índice guardado en `data/index.json`.
- `src/llm_client.py`, `query.py` — pipeline de consulta (k-NN con coseno explícito → contexto → generación). JSON de salida con las 3 claves exactas que pide la consigna.
- `outputs/sample_queries.json` — 3 preguntas reales (dato puntual, sí/no, "cómo hacer"), corridas dos veces: la primera corrida encontró un hallazgo real (el modelo rechazaba una pregunta cuyo chunk recuperado sí tenía la respuesta, por ser demasiado literal con la regla "si no está, decilo"); se ajustó la regla del prompt a "rechazá solo si ningún fragmento se relaciona" y las 3 preguntas pasaron a responder bien. Detalle completo en `modulo-2/README.md`.
- `tests/test_core.py` — 12 tests (chunking, similitud coseno, k-NN, guardado/lectura del índice, contrato JSON de `query.py`), ninguno llama a la API real.
- `README.md` propio con setup, uso, estructura, decisiones técnicas justificadas y el hallazgo documentado.
- **Bonus implementado:** `src/evaluator.py` + `src/evaluate_samples.py`. Puntúa (0-10 + reason) cada entrada de `outputs/sample_queries.json` en 3 dimensiones (relevancia, fidelidad, completitud) y guarda el resultado en `outputs/sample_queries_evaluated.json` — separado, sin tocar el contrato de 3 claves de `sample_queries.json`. Hallazgo real: la primera versión del evaluador acertaba el score pero su `reason` afirmó que faltaba un dato que en realidad estaba en el texto evaluado (error de lectura del propio LLM-juez); se corrigió exigiendo cita textual entre comillas para cada observación. Limitación conocida documentada en el README: un LLM-juez da una señal aproximada, no una verificación formal. 14 tests en total (12 del flujo obligatorio + 2 del evaluador, mockeado).

## Cómo trabajar conmigo en este proyecto

- Priorizar el flujo principal (una llamada que devuelva JSON útil) antes de pulir, iterar el prompt como si fuera código, y armar la estructura de carpetas esperada desde el principio para no migrar después.
- Seguir las reglas globales de `~/.claude/CLAUDE.md` (conventional commits, castellano rioplatense, no hacer build sin pedirlo, plan antes de tocar +2 archivos, etc.) y las reglas transversales de este archivo (branching y framing, ver arriba).
