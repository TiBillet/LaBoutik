window.settingsActivedLogs = function (event) {
	const element = event.target
	if (element.checked) {
		localStorage.setItem("activatedLogs", "true")
		settingsStartLogs()
	} else {
		localStorage.setItem("activatedLogs", "false")
		if (window.settingsLogsContent !== undefined) {
			window.settingsLogsContent = []
			// active fonction  de log originale
			console.log = window.oldLogFunc
			document.querySelector('#settings-logs-content').innerHTML = ''
		}
	}

}


window.showListLogs = function () {
	let logsHtml = ''
	if (window.settingsLogsContent !== undefined && window.settingsLogsContent.length > 0) {
		for (let i = window.settingsLogsContent.length - 1; i >= 0; i--) {
			const msg = window.settingsLogsContent[i]
			// console.log('msg =', msg);
			logsHtml += `<div>${msg}</div>`
		}
	}
	return logsHtml
}

/**
 * Show setting logs UI
 */
window.settingsShowLogs = function () {
	// changer titre
	vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="logs",capitalize">Logs</span>`)

	// TODO: changer la forme du checkbox
	let template = `
	<div class="BF-col-deb l100p h100p" style="font-size: 1.5rem">
		<div class="BF-ligne" style="height: 10%;">
      <label data-i8n="activateLogs" for="settings-launch-logs" class="md16px">activer les logs</label>`

	// etat d'activation des logs
	if (localStorage.getItem("activatedLogs") === "true") {
		template += '<input type="checkbox" id="settings-start-record-logs" checked />'
		// modifie la fonction de log
		if(oldLogFunc === console.log) {
			settingsStartLogs()
		}
	} else {
		template += '<input type="checkbox" id="settings-start-record-logs" />'
		// window.settingsLogsContent = []
	}

	template += '</div>'

	// affiche les messages de logs enregistrés
	template += '<div id="settings-logs-content" class="BF-col-deb" style="height: 90%; overflow:auto;">'
	template += window.showListLogs()

	template += '</div></div>'

	document.querySelector('.content-settings').innerHTML = template

	document.querySelector('#settings-start-record-logs').addEventListener('change', settingsActivedLogs)
}
