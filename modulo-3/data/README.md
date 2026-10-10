# Corpus del Módulo 3 — Nimbus Desk (empresa ficticia)

Documentación interna original de **Nimbus Desk**, una SaaS de help desk. Es contenido escrito
para este proyecto: no proviene de material de terceros ni de documentos reales. Las políticas,
cifras y normas fiscales son ficticias.

| Carpeta | Agente | Documentos | Formatos |
|---|---|---|---|
| `hr_docs/` | HR | vacaciones y licencias, onboarding y desempeño, beneficios y nómina, trabajo híbrido y conducta, FAQ, comunicaciones | `.md`, `.csv`, `.txt` |
| `tech_docs/` | Tech / IT | accesos y contraseñas, VPN y red, equipos y software, mesa de ayuda e incidentes, catálogo de errores, seguridad | `.md`, `.csv`, `.txt` |
| `finance_docs/` | Finance | gastos y reembolsos, facturación a clientes, compras y proveedores, presupuesto y cierre, planes y tarifas, cumplimiento | `.md`, `.csv`, `.txt` |

`python scripts/corpus_stats.py` cuenta unidades (secciones `##`, filas CSV, párrafos `.txt`) y
tokens por documento: ~95 unidades por dominio, de 28 a 126 tokens cada una.

## Zonas de frontera (deliberadas)

Los documentos se referencian entre sí cuando un tema toca varias áreas, igual que en una empresa
real. Esos solapamientos son los casos difíciles para el orquestador y alimentan el golden set:

- **Reembolso de formación o gimnasio:** presupuesto y beneficio en HR; trámite y pago en Finance.
- **Acceso a Nimbus People / Nimbus Expenses:** si no abre, es Tech; el contenido es HR o Finance.
- **Equipos, licencias y compras de software:** pedido en Tech; aprobación de presupuesto en Finance.
- **Recibo de sueldo con error:** HR (nómina), no Finance.
- **Consultas de contratos y cláusulas:** fuera de alcance (área legal; no hay agente de Legal).
