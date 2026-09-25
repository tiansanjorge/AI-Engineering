# Proyecto Integrador — Módulo 2

Chatbot de FAQs con RAG para NimbusHR (HR SaaS ficticio): responde preguntas
de empleados recuperando información real de la documentación interna en
vez de contestar de memoria, y cita los fragmentos que usó para cada
respuesta.

> Este es uno de los módulos del monorepo de la carrera. Ver
> [`../README.md`](../README.md) para el índice general. Todos los
> comandos de abajo asumen que estás parado en esta carpeta (`modulo-2/`).

## Setup

```bash
cd modulo-2                    # si venís de la raíz del repo
python -m venv .venv           # o reusar el venv compartido de la raíz
.venv\Scripts\activate         # en Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # completar OPENAI_API_KEY (o usar el .env compartido en la raíz del repo)
```

## Uso

**1. Indexar el documento** (etapas 1-4: carga → chunking → embeddings → guardado):

```bash
python src/build_index.py
```

Genera `data/index.json` con los chunks y sus embeddings. Solo hace falta
correrlo una vez (o cuando cambie `data/faq_document.txt`).

**2. Consultar** (etapas 1-4: embedding de la pregunta → búsqueda vectorial → contexto → generación):

```bash
python src/query.py "Cuantos dias de PTO acumulo por mes trabajado?"
```

Imprime por stdout el JSON con `user_question`, `system_answer` y
`chunks_related`. Ejemplos reales corridos de punta a punta están en
`outputs/sample_queries.json`.

## Variables de entorno

| Variable          | Descripción                                          |
|--------------------|-------------------------------------------------------|
| `OPENAI_API_KEY`   | Clave de OpenAI. Nunca se hardcodea.                  |
| `EMBEDDING_MODEL`  | Modelo de embeddings (default: `text-embedding-3-small`). |
| `CHAT_MODEL`       | Modelo de chat para generar la respuesta final (default: `gpt-4o-mini`). |

## Tests

```bash
python -m pytest
```

12 tests sobre chunking, similitud coseno, búsqueda k-NN, guardado/lectura
del índice, y el contrato JSON de `query.py`. Ninguno llama a la API real
(`embed_query` y `generate_answer` se mockean) — corren rápido y gratis en
cualquier máquina.

## Estructura

```
modulo-2/
├── data/
│   ├── faq_document.txt        Documento fuente (1747 palabras, 13 secciones)
│   └── index.json               Chunks + embeddings, generado por build_index.py
├── src/
│   ├── chunking.py              Carga del documento + division en chunks
│   ├── embeddings.py            Generacion de embeddings (OpenAI)
│   ├── vector_store.py          Guardado del indice + busqueda k-NN (coseno explicito)
│   ├── llm_client.py            Generacion de la respuesta final (grounded en el contexto)
│   ├── build_index.py           Entrypoint: pipeline de indexacion completo
│   └── query.py                 Entrypoint: pipeline de consulta completo
├── outputs/
│   └── sample_queries.json      3 ejemplos reales de punta a punta
├── tests/
│   └── test_core.py
└── conftest.py                   Permite `import chunking`, `import query`, etc. en los tests
```

## Decisiones técnicas

**Chunking: tamaño fijo con solapamiento** (`chunk_size=100` palabras,
`overlap=20`, ~20%). Se eligió por tres razones: son los parámetros que la
consigna pide documentar explícitamente; sobre un documento de este tamaño
(no miles de páginas) las estrategias más sofisticadas (semántica, por
estructura) no aportan una ventaja medible, según lo comprobado en el
material de referencia del módulo; y el solapamiento mitiga el riesgo de
cortar una oración importante justo en el borde entre dos chunks. Con estos
parámetros, el documento fuente genera 22 chunks de 67 a 100 palabras cada
uno (~90 a ~150 tokens estimados), dentro del rango de 50 a 500 tokens.

**Búsqueda vectorial: k-NN exacto con similitud coseno, calculada a mano
con NumPy** (no una librería de vector store). Se eligió así por dos
razones: la consigna pide que el cálculo de similitud quede explícito y
auditable en el código, no escondido dentro de una librería; y con ~22
chunks, un vector store dedicado no aporta ninguna ventaja de performance
sobre comparar contra todos los vectores (fuerza bruta) — la ventaja de
esas herramientas aparece con miles o millones de vectores, no acá.

## RAG: por qué recuperar antes de generar

El sistema implementa el flujo en dos pasos que define RAG: primero
recupera los chunks más relevantes (`vector_store.search_similar_chunks`),
después los pasa como contexto al LLM (`llm_client.generate_answer`), que
tiene instrucciones explícitas de responder solo con eso. Esto da tres
beneficios sobre un LLM respondiendo de memoria: el conocimiento se
actualiza editando `data/faq_document.txt` y re-indexando, sin re-entrenar
nada; el proceso es transparente (se puede ver exactamente qué recuperó
antes de responder); y la respuesta queda atribuida a fragmentos concretos
de la documentación (`chunks_related`), auditables por quien la lee.

## Un hallazgo real durante las pruebas

Con la primera versión del prompt (regla: "si el contexto no tiene la
respuesta, decilo"), el sistema rechazó una pregunta cuyo chunk recuperado
**sí tenía la respuesta**, pero no con las mismas palabras que la pregunta
("¿puedo ver el historial de sueldos de un ex-empleado?" vs. el chunk, que
hablaba de que el ex-empleado "deja de tener visibilidad... solo para
RRHH"). El modelo fue demasiado literal y no conectó ambas formulaciones.

Se ajustó la regla a "rechazá responder solo si NINGÚN fragmento se
relaciona con la pregunta" (en vez de exigir una coincidencia literal), sin
volver a permitir que complete con conocimiento externo. Con el ajuste, las
3 preguntas de `outputs/sample_queries.json` responden correctamente. El
detalle de las dos corridas está en el historial de commits de esta rama.

## Limitaciones conocidas

- El tamaño de chunk se mide en palabras, no en tokens reales (evita
  depender de una librería de tokenización adicional). Se verificó que la
  aproximación (palabras × 1.3) deja a todos los chunks generados
  cómodamente dentro del rango de 50-500 tokens que pide la consigna.
- La búsqueda es k-NN exacto (fuerza bruta): compara contra todos los
  embeddings guardados. Funciona bien para el tamaño de este documento;
  no escala a un corpus de miles de documentos sin un índice aproximado
  (ANN) o un vector store dedicado.
- El documento fuente es contenido original escrito para este proyecto
  integrador (empresa y políticas ficticias), no un documento real de
  producción.

## Sobre el uso de IA como apoyo

Este código se desarrolló con Claude Code como asistente, siguiendo el
mismo criterio que en el Módulo 1: las decisiones de diseño (chunking,
método de búsqueda, alcance del bonus) se discutieron y confirmaron
explícitamente antes de implementar. El hallazgo documentado arriba (regla
del prompt demasiado literal) se detectó corriendo el sistema real contra
preguntas de prueba, no a priori — se ajustó con evidencia, no a ojo.

**Material de referencia.** Claude Code tuvo acceso de solo lectura a las
lecturas del módulo, a la consigna del proyecto integrador y al repositorio
de ejemplos del profesor (`material/`, fuera de este repo vía
`.gitignore`), usados como referencia de convenciones y del enunciado,
nunca como destino de escritura ni como fuente copiada del documento
fuente (`data/faq_document.txt` es contenido original). El límite de
lectura/escritura sobre `material/` está configurado en `CLAUDE.md`.
