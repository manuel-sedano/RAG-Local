# Comercialización del MVP — Plataforma RAG Local

**Documento orientado a:** venta a empresas y a instituciones de educación superior (referencia: **UAEM** — *Universidad Autónoma del Estado de Morelos* — u otras universidades públicas en México).  
**Fecha de referencia:** mayo de 2026.  
**Moneda de referencia:** MXN (pesos mexicanos). Los rangos son orientativos y dependen del alcance real del entregable, garantías, soporte y formalización contractual.

---

## 1. Resumen ejecutivo

El proyecto **Plataforma RAG Local** es una **plataforma de conocimiento con IA generativa local (RAG)**: permite cargar documentos (PDF, DOCX, TXT), indexarlos con embeddings y metadatos, consultarlos en lenguaje natural con **citas a fuentes**, con énfasis en **operación local** (soberanía de datos, sin depender de APIs cloud obligatorias), **seguridad operativa** (proxy, controles de acceso, límites de uso, saneamiento de archivos) y **observabilidad** (métricas y logs).

En la comercialización como **MVP ya hecho**, la oferta no se reduce a “código”: incluye **tiempo de mercado**, **reducción de riesgo técnico** y un **punto de partida** para producción interna del adquirente. La fijación del precio puede alinearse con: (a) valor percibido por el comprador, (b) costo de oportunidad de construir equivalente internamente, (c) transferencia de conocimiento y (d) obligaciones posteriores (soporte, garantías, actualizaciones).

---

## 2. Componentes de la oferta

Tres “capas” de valor frecuentes en ofertas B2B e institucionales:

| Capa | Qué incluye (conceptualmente) | Por qué la compran |
|------|--------------------------------|--------------------|
| **Producto / software** | Repositorio, configuración base, documentación de despliegue | Evitan 3–9 meses de desarrollo exploratorio |
| **Implementación** | Instalación en su infra, ajuste de variables, pruebas de aceptación | Que “funcione en su mundo” (red, políticas, hardware) |
| **Operación y adopción** | Capacitación, manual de administración, SLA opcional | Que lo usen de verdad y no quede abandonado |

La venta limitada a la primera capa suele implicar menor precio pero más fricción si el cliente carece de equipo técnico sólido. Los paquetes **software + implementación + capacitación** suelen soportar precios más altos y menos disputas postventa.

---

## 3. Áreas que se benefician

### 3.1 En empresas (sector privado)

- **Legal y cumplimiento:** consulta interna sobre contratos, políticas y normativas con trazabilidad (citas) y datos sin salir del perímetro acordado.  
- **Recursos humanos:** manuales, beneficios, procesos, onboarding; reduce carga en mesa de ayuda si está bien gobernado.  
- **Operaciones y cadena de suministro:** procedimientos, especificaciones, checklists, incidentes recurrentes.  
- **Ventas y customer success:** respuestas basadas en documentación oficial de producto (menos “alucinaciones” si el RAG está bien configurado).  
- **Calidad / manufactura / ingeniería:** normas internas, BOM, reportes de no conformidad (siempre con revisión humana en decisiones críticas).  
- **TI / seguridad / arquitectura:** conocimiento interno de sistemas, runbooks, postmortems; útil como **segundo cerebro** si el acceso está restringido por roles.

### 3.2 En una universidad (UAEM — Universidad Autónoma del Estado de Morelos — u otras IES)

- **Biblioteca y gestión del conocimiento:** asistente sobre guías, bases de datos académicas (según derechos), normativos institucionales **ya digitalizados y con permiso de uso**.  
- **Secretaría académica / registro:** orientación sobre reglamentos y trámites (con disclaimers legales claros: no sustituye resoluciones oficiales).  
- **Investigación (unidades y laboratorios):** búsqueda semántica sobre corpus propio (papers internos, reportes, datos ya publicables).  
- **Vinculación y extensión:** material para empresas y comunidad, FAQs complejas.  
- **Planeación y transparencia:** apoyo a consulta de informes y documentos ya públicos (cuidando versiones oficiales y fechas).  
- **Centro de cómputo / innovación educativa:** piloto de IA soberana alineado a políticas de privacidad estudiantil.

**Universidades:** material con **derechos de autor** o **datos personales** queda sujeto a LFPDPPP y lineamientos internos; el contrato delimita corpus indexable y responsable del tratamiento.

---

## 4. Cómo fijar precio (marco práctico)

### 4.1 Métodos que aceptan compradores institucionales y empresariales

1. **Costo evitado (build vs buy):** estimar equipo (PM + backend + frontend + ML + DevOps) × meses × costo cargado. Aunque el MVP no sustituye un equipo completo, reduce meses de “callejón sin salida”.  
2. **Valor del caso de uso:** ahorro en horas-hombre de especialistas (legal, soporte N2, analistas) o reducción de riesgo operativo.  
3. **Comparativo de mercado:** licencias de software empresarial + consultoría; incluso sin marca consolidada, el comparativo ancla la conversación.  
4. **Costo total de propiedad (TCO):** hardware local, electricidad, administración; la propuesta basada en despliegue local destaca **control de datos** y previsibilidad frente a consumo por tokens en nube.

### 4.2 Variables que suben o bajan el precio

**Suben el precio de forma justificada:**

- Implementación en sitio o en su nube privada con pruebas de aceptación firmadas.  
- Integración con identidad institucional (LDAP/SAML) si está en alcance.  
- Hardering adicional, auditoría básica, plan de respaldo y recuperación.  
- Capacitación para administradores y “power users”.  
- Soporte con tiempos de respuesta acordados (SLA).  
- Transferencia de propiedad intelectual clara (cesión de código) o licenciamiento exclusivo por territorio/sector.

**Bajan el precio o exigen descuento:**

- Compra “solo código” sin implementación.  
- El comprador exige garantías amplias sin pago de soporte.  
- Proceso de licitación con competencia y presupuesto máximo fijo.  
- Dependencias de hardware específico que el cliente no tiene.

---

## 5. Rangos de precio recomendados (México, MVP entregado)

Los rangos parten de un **MVP funcional** con documentación de despliegue. Suben con entregables adicionales (integraciones, seguridad reforzada, multi-tenant robusto, etc.).

### 5.1 Empresas (PYME y medianas)

| Oferta | Contenido típico | Rango orientativo (MXN) |
|--------|-------------------|-------------------------|
| **A — Licencia + entrega** | Código/documentación, 1 handover, sin SLA | **$80,000 – $250,000** |
| **B — Paquete estándar** | A + instalación guiada, 2–4 sesiones de capacitación, 30 días de soporte correctivo | **$180,000 – $450,000** |
| **C — Profesional** | B + hardening básico, plan de backups, criterios de aceptación, 90 días de soporte | **$350,000 – $900,000** |

**Suscripción / mantenimiento anual (opcional):** como regla práctica, **15%–25%** del precio del paquete por año si incluye actualizaciones menores, soporte y compatibilidad; o un monto fijo mensual **$8,000 – $35,000 MXN/mes** según SLA y tamaño de la empresa.

### 5.2 Universidad pública (UAEM — Morelos — u otra IES) — compra formal

Compras en universidades públicas: **concurso, invitación a tres, o adjudicación directa** según monto y normativa. Variables de precio:

- Presupuesto disponible y tope del proceso.  
- Entregables auditables (actas, evidencias, capacitación, garantía).  
- Posible **descuento social** o académico respecto a la lista empresarial de referencia, compensado con **reconocimiento institucional**, carta de recomendación o permiso de citar el caso como referencia (si el proveedor lo acepta).

| Oferta | Contenido típico | Rango orientativo (MXN) |
|--------|-------------------|-------------------------|
| **U1 — Licenciamiento académico** | Entrega para unidad piloto, documentación, 1 capacitación | **$120,000 – $350,000** |
| **U2 — Piloto + producción acotada** | U1 + implementación, aceptación formal, 6–12 meses soporte ligero | **$280,000 – $750,000** |
| **U3 — Campus / varias dependencias** | U2 + multi-unidad, más horas de acompañamiento | **$600,000 – $1,800,000+** |

Licitación con competencia: desglose por partidas (software, servicios profesionales, capacitación, soporte) y transparencia frente a “caja negra”.

### 5.3 Referencia en USD (solo ancla mental)

A tipo de cambio variable, **$5,000 – $25,000 USD** para paquetes PYME medianos con implementación y soporte corto es un orden de magnitud frecuente en ventas B2B de software especializado hecho a medida; **no** es una promesa de mercado, solo ancla para negociación.

---

## 6. Argumentos de precio (referencia)

1. **Tiempo al valor:** el MVP acorta el ciclo de prueba de concepto a producción interna en semanas, frente a meses de construcción desde cero.  
2. **Soberanía y privacidad:** los documentos y consultas pueden mantenerse en infraestructura bajo control del adquirente, alineado a políticas de datos y aversiones al envío de información sensible a terceros.  
3. **Trazabilidad:** el enfoque con citas/fuentes reduce la confianza ciega en la IA y apoya auditoría de respuestas en procesos internos.  
4. **Costo predecible vs nube:** se evitan costos variables por tokens y sorpresas de facturación cuando el volumen de uso crece.  
5. **Riesgo técnico acotado:** el stack es conocido (contenedores, servicios separados), con observabilidad y prácticas de seguridad operativa como punto de partida.  
6. **Transparencia comercial:** el precio puede desglosarse por licencia, implementación, capacitación y soporte; el adquirente paga por entregables verificables.

En universidades, argumentos recurrentes: **alineación a educación e investigación**, **piloto en una dependencia**, **plan de gobernanza de datos**.

---

## 7. Estrategia de venta (referencia)

- **Empresas:** el **paquete B** como oferta por defecto; el **paquete A** cuando el cliente priorice costo inicial bajo y acepte limitación explícita de soporte.  
- **UAEM (Universidad Autónoma del Estado de Morelos):** orientación a **U1/U2** con piloto; escalamiento a U3 tras evidencia de uso y resultados (menor fricción política tras un primer despliegue exitoso).  
- **Mensajes a evitar:** promesas del tipo “reemplaza abogados/médicos/contadores” o “100% preciso”; el posicionamiento adecuado es **asistente de conocimiento** con supervisión humana.

---

## 8. Aspectos legales y contractuales (mínimo imprescindible)

- **Propiedad intelectual:** licencia no exclusiva vs cesión total (la cesión suele costar más).  
- **Garantía:** corrección de defectos por un período corto; exclusiones por cambios del cliente.  
- **Responsabilidad:** límite de responsabilidad razonable; la salida del modelo no constituye asesoría legal/médica/fiscal.  
- **Datos personales:** quién es responsable del tratamiento; prohibiciones de indexar ciertos datos sin base legal.  
- **Confidencialidad y seguridad:** NDAs si hay información sensible en la implementación.

*(Apartado informativo; revisión jurídica externa ante contrato formal.)*

---

## 9. Checklist antes de cotizar

- [ ] Delimitar qué está **incluido** y **excluido** en el alcance (hardware, integraciones, SSO, multi-idioma).  
- [ ] Establecer número de horas de implementación y tarifa por hora excedente.  
- [ ] Documentar criterios de aceptación medibles (por ejemplo: ingestión de X documentos, latencia objetivo, prueba de recuperación).  
- [ ] Especificar modelo de actualización (por ejemplo: Git, releases, meses de soporte).  
- [ ] Elaborar **hoja de costo interno** del proveedor para evitar precios por debajo del costo real de entrega.

---

## 10. Infraestructura necesaria para operación adecuada

Arquitectura: **varios servicios en contenedores** (Docker Compose)—API, frontend, colas, base relacional, vectorial, LLM local, proxy inverso y, según despliegue, seguridad y observabilidad. Carga conjunta sobre CPU, RAM, disco y, si aplica, **GPU** (no equivale a un único binario ligero).

### 10.1 Modelo de despliegue

| Escenario | Descripción | Uso típico |
|-----------|-------------|------------|
| **Estación de trabajo (referencia proyecto)** | Windows 11 + WSL2 (Ubuntu 22.04) + Docker Desktop con integración WSL2 | Desarrollo, pruebas, demos, piloto muy pequeño |
| **Servidor Linux dedicado** | Una máquina física o VM con Docker Engine / Compose (sin depender de WSL2) | Producción en empresa o universidad |
| **Nube privada / VM institucional** | Misma idea que servidor Linux; políticas de red y respaldos a cargo del cliente | Cuando no hay servidor físico en sitio |

**Producción típica (empresa o UAEM):** **Linux + Docker** en servidor dedicado (físico o VM). **WSL2:** entorno de desarrollo o laboratorio; no sustituye el patrón de centro de datos en Linux.

### 10.2 Hardware — referencia “objetivo” del proyecto

**Referencia de hardware** (alineada con `README.md` / documentación de despliegue):

| Recurso | Especificación orientativa | Comentario |
|---------|----------------------------|------------|
| **CPU** | 8 núcleos físicos o más (p. ej. clase Ryzen 7 / Xeon / EPYC equivalente) | Indexación, embeddings, API y contenedores en paralelo cargan el CPU |
| **RAM** | **32 GB** como referencia cómoda | Con menos RAM (16 GB) puede funcionar un piloto **reduciendo** servicios simultáneos, tamaño de modelo y carga; no es ideal para producción multiusuario |
| **GPU** | Opcional pero **muy recomendada** para el LLM local; p. ej. **12 GB VRAM** en referencia | Sin GPU, inferencia en CPU es posible pero **más lenta** y puede afectar experiencia de chat concurrente |
| **Almacenamiento** | **1 TB NVMe SSD** (referencia) | Modelos de lenguaje, embeddings, índices vectoriales, PostgreSQL, subidas y logs crecen con el uso; HDD solo para archivos fríos, no recomendado para DB/vectores activos |
| **Red** | Gbit Ethernet estable; baja latencia interna si hay usuarios en LAN/VPN | El streaming de respuestas y subida de documentos benefician red estable |

### 10.3 Hardware — mínimos y producción (orientación comercial)

Tres **perfiles** de dimensionamiento en cotizaciones o licitaciones (validación con TI del cliente):

| Perfil | RAM | CPU | GPU | Disco | Uso razonable |
|--------|-----|-----|-----|-------|----------------|
| **Piloto / demo** | 16–32 GB | 4–8 núcleos | Opcional (mejor si hay) | 256–512 GB SSD | Pocos usuarios, pocos documentos, horario acotado |
| **Producción PYME** | **32 GB** | 8+ núcleos | Recomendada (8+ GB VRAM) | **512 GB–1 TB** SSD | Uso diario, varias KB, varios usuarios concurrentes moderados |
| **Institucional / alto volumen** | **64 GB+** | 16+ núcleos / 2 sockets según carga | GPU mayor o varias GPUs según política de colas | **1 TB+** SSD (+ respaldo) | Muchos documentos, indexación frecuente, más usuarios; puede requerir **varios nodos** o revisión arquitectónica (fuera de MVP típico) |

**Memoria y disco:** componentes típicos—(1) imágenes Docker, (2) volúmenes PostgreSQL y Qdrant, (3) modelos Ollama, (4) cola y resultados de trabajos, (5) **uploads**, (6) logs/métricas con Prometheus/Grafana/Loki activos.

### 10.4 Sistema operativo y software base

| Componente | Requisito / recomendación |
|------------|---------------------------|
| **SO (desarrollo tipo repo)** | **Windows 11** + **WSL2** con **Ubuntu 22.04** + **Docker Desktop** (integración WSL2) + **Git** |
| **SO (producción recomendada)** | **Linux 64-bit** (p. ej. Ubuntu 22.04 LTS o equivalente servidor), kernel y paquetes al día, **Docker Engine** y **Docker Compose plugin** |
| **Contenedores** | **Docker Compose** según manifiesto del proyecto; host con **volúmenes** y **redes** requeridos |
| **Virtualización** | Si es VM: anidación y recursos **fijos** (no “burst” mínimo) para evitar latencia en inferencia e indexación |

### 10.5 Red, puertos y exposición

- El diseño típico expone la aplicación a través de un **proxy inverso** (p. ej. Traefik): en escenario local suele ser **HTTP en 80** (y **443** si hay TLS).  
- **Firewall:** superficie mínima hacia el exterior; bases de datos, broker, vector DB y Ollama en **red interna de Compose**.  
- **TLS/HTTPS:** certificado válido (interno o público) y política de seguridad acorde al organismo.  
- **Acceso institucional:** VPN, segmentación VLAN o reglas de NSG si aplica en nube.

### 10.6 Capacidad y escalabilidad

- **Usuarios y documentos:** el límite práctico lo marcan RAM, velocidad de disco, tamaño del modelo y política de **colas** (trabajos de ingesta pueden ser intensivos).  
- **Copias de seguridad:** PostgreSQL, volúmenes Qdrant, configuración (`.env` fuera del repositorio), carpeta de modelos si aplica.  
- **Alta disponibilidad:** despliegue en un solo host sin cluster HA; objetivo 99.9% implica **diseño adicional** y costo aparte.

### 10.7 Checklist de infraestructura (para anexar a cotización)

- [ ] Servidor o VM dedicada con recursos del perfil acordado (piloto vs producción).  
- [ ] Linux + Docker instalados y política de actualizaciones definida.  
- [ ] Disco SSD suficiente para datos + crecimiento anual estimado.  
- [ ] GPU acordada (modelo y drivers) si se exige rendimiento de chat aceptable.  
- [ ] Red: DNS interno, certificados, reglas de firewall y acceso de administradores.  
- [ ] Respaldo y restauración probados al menos una vez en el entorno del cliente.

---

## 11. Conclusión

Para un **MVP ya construido** de una plataforma RAG local con documentación y enfoque de seguridad/operación, una estrategia sólida en México incluye:

- Cotizar **por paquetes** (no solo el repositorio).  
- Anclar el precio al **ahorro de tiempo**, **control de datos** y **entregables verificables**.  
- Hacia instituciones de educación superior, estructurar **piloto** con precio y alcance acotados, y escalar con evidencia.

Los rangos (§5) varían con el **avance real del código** (implementado vs planificado), el **tamaño del cliente** y la **política de soporte postventa** del proveedor. El bloque de infraestructura (§10) se usa como anexo técnico en propuestas para **hardware, SO y operación**.
