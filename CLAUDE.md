# Contexto — Proyectos Integradores, carrera AI Engineering (Henry)

Este repo (`AI-Engineering`) es el destino de **todas** las entregas de la carrera, módulo a módulo (Módulo 1, 2, 3, 4...), no solo la actual. Las secciones de "Reglas transversales" abajo aplican a todos los módulos; el resto del documento hoy describe el Módulo 1 en curso y se irá actualizando/ampliando por módulo a medida que avancen.

## Reglas transversales (todos los módulos)

**Framing de negocio preferido (decisión 2026-09-11, aplica a toda la carrera):** cuando la consigna de un módulo deja espacio de elección (ejemplos, dominio de datos, vocabulario, tipo de acciones/casos de uso), inclinarse por defecto hacia un dominio de **Help Desk / soporte al cliente vía tickets**, en línea con una propuesta de proyecto Full Stack más grande que estoy evaluando por fuera de esta carrera (notas privadas en `HelpDesk - Proyecto Full Stack.txt`, gitignoreado, no es un entregable). **La consigna de cada módulo manda siempre por encima de este framing** — si en algún punto entran en conflicto, gana la consigna.

**Branching (decisión 2026-09-11, aplica a toda la carrera):** `develop` + feature branches cortas, siguiendo la skill `git-workflow-and-versioning`. Nunca commitear directo a `main`.
1. Cada objetivo/módulo va en su propia rama corta (`feature/...`) que mergea a `develop`.
2. `main` se actualiza solo con un merge deliberado y explícitamente pedido desde `develop`.

## Qué es este workspace

El workspace tiene tres carpetas **hermanas, sin jerarquía real en el filesystem**:

| Carpeta | Rol | ¿Se puede escribir? |
|---|---|---|
| `AI-Engineering` (esta carpeta) | Mi proyecto integrador (repo clonado de `tiansanjorge/AI-Engineering` en GitHub). Todo el código, commits y entregables van acá. | **Sí, únicamente acá.** |
| `Profe modulo 1` | Material del profesor visto en clase (tiene su propio repo git). Es referencia. | **No. Nunca.** |
| `Material Modulo 1` | Lecturas (LECTURE 1-4) y la consigna oficial del proyecto integrador. | **No. Nunca.** |

### Regla dura de seguridad
`Profe modulo 1` aparece como additional working directory en este entorno, así que técnicamente hay acceso de lectura y escritura ahí — nada lo bloquea a nivel de plataforma. Por eso, como regla explícita:

- **Nunca** editar, crear, borrar ni mover archivos dentro de `Profe modulo 1` o `Material Modulo 1`.
- **Nunca** correr comandos git (`git add/commit/push/checkout/etc.`) apuntando a `Profe modulo 1` — tiene su propio repo y no es el mío.
- Antes de cualquier operación de escritura o comando destructivo, confirmar que la ruta absoluta empieza con `...\Henry - AI Engineering\AI-Engineering\`.
- Esas dos carpetas se leen solo como consulta puntual (ver cómo resolvió algo el profe, releer una lectura), nunca como destino de una acción.

## El proyecto integrador: "Multitasking Text Utility"

Consigna extraída de `Material Modulo 1/Consignas y Guia proyecto integrador.docx`.

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

## Estado actual del proyecto (al 2026-09-11)

- Repo git con remote `origin` en `git@github.com:tiansanjorge/AI-Engineering.git`. Ramas `main` y `develop` ya creadas y pusheadas, con el flujo de branching transversal activo (ver arriba).
- Hay un MVP mínimo exploratorio, no la estructura final:
  - [index.py](index.py) — llamada básica a `openai` con `dotenv`, sin JSON estructurado ni métricas todavía.
  - [testing.py](testing.py) — notas/output de ejemplo de `completion.usage`, no es un test real (no usa pytest/unittest).
  - [requirements.txt](requirements.txt) — solo `openai` y `python-dotenv`.
  - `.env` / `.env.example` — ya con placeholder de `OPENAI_API_KEY`.
- Nada de esto sigue todavía la estructura de carpetas esperada (`src/`, `prompts/`, `metrics/`, `reports/`, `tests/`) — es el próximo paso de organización, no algo ya resuelto.

## Cómo trabajar conmigo en este proyecto

- Priorizar el flujo principal (una llamada que devuelva JSON útil) antes de pulir, iterar el prompt como si fuera código, y armar la estructura de carpetas esperada desde el principio para no migrar después.
- Seguir las reglas globales de `~/.claude/CLAUDE.md` (conventional commits, castellano rioplatense, no hacer build sin pedirlo, plan antes de tocar +2 archivos, etc.) y las reglas transversales de este archivo (branching y framing, ver arriba).
