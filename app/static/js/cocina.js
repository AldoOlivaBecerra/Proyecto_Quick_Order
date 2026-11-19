/**
 * QUICK ORDER - Monitor de Cocina (Kitchen Display System - KDS)
 * Incremento 3: Módulo de Cocina
 * 
 * Implementa Short Polling cada 1.5 segundos para reflejar en tiempo real
 * nuevas órdenes creadas en caja y cambios de estado sin recargar la página.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.info('QUICK ORDER - Monitor KDS inicializado.');
    inicializarMonitorCocina();
});

function inicializarMonitorCocina() {
    const INTERVALO_POLLING_MS = 1500; // 1.5 segundos (cumple la meta de <= 3s)
    let pollingActivo = true;
    let ultimoPayloadHash = '';

    const containerPendientes = document.getElementById('container-pendientes');
    const containerPreparacion = document.getElementById('container-preparacion');
    const metricPendientes = document.getElementById('metric-pendientes');
    const metricPreparacion = document.getElementById('metric-preparacion');
    const metricTotal = document.getElementById('metric-total');
    const badgePendientes = document.getElementById('badge-count-pendientes');
    const badgePreparacion = document.getElementById('badge-count-preparacion');
    const syncStatus = document.getElementById('sync-status');

    if (!containerPendientes || !containerPreparacion) {
        return;
    }

    // 1. Delegación de eventos para botones de acción (Iniciar y Finalizar)
    document.addEventListener('click', async (event) => {
        const btnIniciar = event.target.closest('.btn-action-iniciar');
        const btnFinalizar = event.target.closest('.btn-action-finalizar');

        if (btnIniciar) {
            const comandaId = btnIniciar.dataset.id;
            await ejecutarTransicion(comandaId, 'iniciar', btnIniciar);
        } else if (btnFinalizar) {
            const comandaId = btnFinalizar.dataset.id;
            await ejecutarTransicion(comandaId, 'finalizar', btnFinalizar);
        }
    });

    /**
     * Envía la petición asíncrona de transición a la API de Cocina
     */
    async function ejecutarTransicion(comandaId, accion, boton) {
        if (!comandaId) return;
        boton.disabled = true;
        const textoOriginal = boton.innerHTML;
        boton.innerHTML = '⏳ Procesando...';

        try {
            const endpoint = `/cocina/api/comandas/${comandaId}/${accion}`;
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Sincronizar inmediatamente el monitor tras la acción exitosa
                await consultarComandasActivas();
            } else {
                alert(`Aviso de cocina: ${data.error || 'No se pudo completar la operación.'}`);
                boton.disabled = false;
                boton.innerHTML = textoOriginal;
                await consultarComandasActivas();
            }
        } catch (error) {
            console.error(`Error al ejecutar acción ${accion} sobre comanda #${comandaId}:`, error);
            alert('Error de comunicación con el servidor de cocina.');
            boton.disabled = false;
            boton.innerHTML = textoOriginal;
        }
    }

    /**
     * Consulta el endpoint JSON ligero cada 1.5s
     */
    async function consultarComandasActivas() {
        try {
            const response = await fetch('/cocina/api/activas', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                marcarEstadoSincronizacion(false);
                return;
            }

            const data = await response.json();
            if (!data.success) {
                marcarEstadoSincronizacion(false);
                return;
            }

            marcarEstadoSincronizacion(true);

            // Generar hash simple de estado para evitar re-renderizar el DOM si no hay cambios
            const payloadHash = JSON.stringify({
                total: data.total,
                p: data.pendientes.map(x => [x.comanda_id, x.estado, x.fecha_hora_actualizacion]),
                e: data.en_preparacion.map(x => [x.comanda_id, x.estado, x.fecha_hora_actualizacion])
            });

            if (payloadHash === ultimoPayloadHash) {
                // No hay cambios de estado ni nuevas comandas: conservar DOM
                return;
            }

            ultimoPayloadHash = payloadHash;
            actualizarTablero(data);

        } catch (err) {
            console.warn('Fallo en sincronización periódica de cocina:', err);
            marcarEstadoSincronizacion(false);
        }
    }

    /**
     * Actualiza el indicador visual de conexión en vivo
     */
    function marcarEstadoSincronizacion(enLinea) {
        if (!syncStatus) return;
        const dot = syncStatus.querySelector('.sync-dot');
        if (enLinea) {
            if (dot) dot.className = 'sync-dot live';
            syncStatus.innerHTML = '<span class="sync-dot live"></span> En vivo (1.5s)';
            syncStatus.className = 'sync-badge sync-online';
        } else {
            if (dot) dot.className = 'sync-dot reconectando';
            syncStatus.innerHTML = '<span class="sync-dot reconectando"></span> Reconectando...';
            syncStatus.className = 'sync-badge sync-warning';
        }
    }

    /**
     * Renderiza las tarjetas de forma segura en las 2 columnas del KDS
     */
    function actualizarTablero(data) {
        // Actualizar contadores métricos
        if (metricPendientes) metricPendientes.textContent = data.pendientes.length;
        if (metricPreparacion) metricPreparacion.textContent = data.en_preparacion.length;
        if (metricTotal) metricTotal.textContent = data.total;
        if (badgePendientes) badgePendientes.textContent = data.pendientes.length;
        if (badgePreparacion) badgePreparacion.textContent = data.en_preparacion.length;

        // 1. Renderizar columna Pendientes
        if (data.pendientes.length === 0) {
            containerPendientes.innerHTML = `
                <div class="kds-empty-column" id="empty-pendientes">
                    <span class="empty-icon">☕</span>
                    <p class="empty-title">Sin órdenes pendientes</p>
                    <p class="empty-sub">Las nuevas comandas registradas en caja aparecerán aquí automáticamente.</p>
                </div>
            `;
        } else {
            containerPendientes.innerHTML = data.pendientes.map(c => generarTarjetaHtml(c, 'pendiente')).join('');
        }

        // 2. Renderizar columna En Preparación
        if (data.en_preparacion.length === 0) {
            containerPreparacion.innerHTML = `
                <div class="kds-empty-column" id="empty-preparacion">
                    <span class="empty-icon">🧑‍🍳</span>
                    <p class="empty-title">Sin órdenes en curso</p>
                    <p class="empty-sub">Inicie una orden pendiente para comenzar su preparación.</p>
                </div>
            `;
        } else {
            containerPreparacion.innerHTML = data.en_preparacion.map(c => generarTarjetaHtml(c, 'en preparación')).join('');
        }
    }

    /**
     * Genera la estructura HTML de cada tarjeta de pedido
     */
    function generarTarjetaHtml(comanda, estado) {
        const esPendiente = estado === 'pendiente';
        const cardClass = esPendiente ? 'card-pendiente' : 'card-preparacion';
        const tiempoTexto = esPendiente 
            ? `⏰ ${comanda.fecha_hora_creacion}` 
            : '🔥 En cocina';

        const botonHtml = esPendiente
            ? `<button type="button" class="btn btn-kds-start btn-action-iniciar" data-id="${comanda.comanda_id}">
                   ▶️ Empezar Preparación
               </button>`
            : `<button type="button" class="btn btn-kds-finish btn-action-finalizar" data-id="${comanda.comanda_id}">
                   ✅ Marcar como Lista
               </button>`;

        const itemsHtml = comanda.items.map(item => `
            <li class="kds-item-row">
                <span class="kds-item-qty">${item.cantidad}x</span>
                <div class="kds-item-info">
                    <span class="kds-item-name">${escapeHtml(item.producto_nombre)}</span>
                    ${item.especificaciones ? `<span class="kds-item-spec">📝 ${escapeHtml(item.especificaciones)}</span>` : ''}
                </div>
            </li>
        `).join('');

        return `
            <article class="kds-card ${cardClass}" id="card-comanda-${comanda.comanda_id}" data-id="${comanda.comanda_id}" data-estado="${estado}">
                <div class="kds-card-header">
                    <span class="kds-card-id">#${comanda.comanda_id}</span>
                    <span class="kds-card-time" title="Registro">${escapeHtml(tiempoTexto)}</span>
                </div>
                <div class="kds-card-items">
                    <ul class="kds-items-list">
                        ${itemsHtml}
                    </ul>
                </div>
                <div class="kds-card-footer">
                    ${botonHtml}
                </div>
            </article>
        `;
    }

    function escapeHtml(texto) {
        if (!texto) return '';
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }

    // Iniciar temporizador de Short Polling
    const temporizadorId = setInterval(consultarComandasActivas, INTERVALO_POLLING_MS);

    // Limpieza si se abandona la página
    window.addEventListener('beforeunload', () => {
        clearInterval(temporizadorId);
    });
}
