window.settingsShowInfos = function () {
	// changer titre
	vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="infos",capitalize">Infos</span>`)

	document.querySelector('.content-settings').innerHTML = `
	<h1>Infos</h1>
	`
}

/**
 * Change language
 */
window.changeLanguageAction = async function () {
	console.log("-> changeLanguageAction !")
	// récupération de la valeur entrée
	const selectLanguage = document.querySelector('input[type="radio"][name="select-language"]:checked').value
	// console.log('selectLanguage =', selectLanguage)
	localStorage.setItem("language", selectLanguage)
	// POST le changement de langue au serveur et recharge la page
	try {
		const body = new URLSearchParams()
		body.append('csrfmiddlewaretoken', glob.csrf_token)
		body.append('language', selectLanguage)
		const response = await fetch(`/i18n/setlang/`, { method: 'post', body })
		if (response.status === 200) {
			window.location.reload()
		} else {
			throw Error(data.message)
		}
	} catch (error) {
		console.log('-> fetcht  =', error)
	}

}

/**
 * Show change language UI
 */
window.settingsChangeLanguage = function () {
	const local = localStorage.getItem("language")
	const data = getLanguages()

	// changer titre
	vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="language",capitalize">Langue</span>`)

	let template = `<div id="settings-ui-language" class="BF-col l100p h100p">
    <h1 data-i8n="selectLanguage,capitalize" style="color: #ffffff; margin-bottom: 4px;">Sélectionner une langue</h1>
    <h2 data-i8n="appWillBeRecharged" style="margin-top: 0; margin-bottom: 2rem">L'application sera rechargée.</h2>
    <div class="BF-col" style="margin: 0 4rem;">`

	for (let i = 0; i < data.length; i++) {
		const langue = data[i].language
		const label = data[i].infos

		if (langue === local) {
			template += `<div style="margin-bottom: 3rem;">
        <input type="radio" id="language-${i}" name="select-language" value="${langue}" checked />
        <label for="language-${i}" style="font-size: 1.5rem;">${label}</label>
      </div>`
		} else {
			template += `<div style="margin-bottom: 3rem;">
        <input type="radio" id="language-${i}" name="select-language" value="${langue}" />
        <label for="language-${i}" style="font-size: 1.5rem;">${label}</label>
      </div>`
		}

	}
	template += `</div>
  <div class="BF-ligne-entre">
    <bouton-basique traiter-texte="1" texte="VALIDER|1.5rem||validate-uppercase" couleur-fond="#339448" icon="fa-check-circle||2rem" width="240px" height="100px"  onclick="changeLanguageAction();" style="margin: 8px;"></bouton-basique>
  </div>
  </div>`

	document.querySelector('.content-settings').innerHTML = template
	translate('#settings-ui-language')
}

window.settingsShowLogs = function () {
	// changer titre
	vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="logs",capitalize">Logs</span>`)

	document.querySelector('.content-settings').innerHTML = `
	<h1>Logs</h1>
	`

}

window.settingsLaunchAction = function (ev) {
	const cible = ev.target
	const action = cible.classList.contains("target-settings") === true ? cible.getAttribute('action') : null

	if (action !== null && window[action] !== undefined) {
		window[action]()
	}

	if (window[action] === undefined) {
		console.log(getTranslate('functionSettingsNotExist').replace('{replace}', action))
	}
}

/**
 * Show settings UI
 * @returns {void}
 */
window.showSettingsInterface = function () {
	/**
	 * @type {Array<object>}
	 */
	const settingsActions = [
		{ title: 'infos', icon: 'fa-info', func: 'settingsShowInfos' },
		{ title: 'language', icon: 'fa-language', func: 'settingsChangeLanguage' },
		{ title: 'logs', icon: 'fa-stethoscope', func: 'settingsShowLogs' }
	]

	// efface le menu
	document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
	// éfface les autres élément(pages)
	sys.effacerElements(['#page-commandes', '#tables', '#commandes-table'])
	// rend visible l'élément(page) '#service-commandes'
	sys.afficherElements(['#service-commandes,block'])

	// changer titre
	vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="${settingsActions[0].title},capitalize">Infos</span>`)

	const style = `
	<style>
	#service-commandes {
		--width-nav-settings: 20%;
	}

	.nav-settings {
		width: var(--width-nav-settings);
		height: 100%;
		background-color: var(--bleu09);
		color: var(--blanc01);
		overflow-y: scroll;
		border-left: 1px solid var(--bleu10);
	}

	.bt-settings {
		position: relative;
		width: 98%;
		height: 60px;
		border-bottom: 1px solid var(--bleu10);
		margin: 4px 0;
	}

	.target-settings {
		position: absolute;
		left: 0;
		top: 0;
		width: 98%;
		height: 60px;
		opacity: 0;
	}

	.content-settings {
		width: calc(100% - var(--width-nav-settings));
		height: 100%;
		background-color: var(--bleu09);
		color: var(--blanc01);
		overflow-y: scroll;
	}
	</style>`

	let template = `
	<div class="BF-ligne l100p h100p">
		<div class="BF-col-deb nav-settings">`

	settingsActions.forEach(action => {
		template += `<div class="BF-col bt-settings">
		<i class="fas ${action.icon} mb4px"></i>
		<span>${action.title}</span>
		<div class="target-settings" action="${action.func}"></div>
		</div>`
	})

	template += `
		</div>
		<div class="BF-col-deb content-settings"></div>
	</div>`

	document.querySelector('#service-commandes').innerHTML = style + template

	// event listener
	document.querySelector('.nav-settings').addEventListener('click', settingsLaunchAction)

	/*
	// sauvegarder ancienne fonctio log
	window.oldLogFunc = console.log

	// modifier fonction log - utilise le store
	window.console.log = function (message) {
		// mon log
		document.querySelector('#logs').insertAdjacentElement('beforebegin', `<p>${message}</p>`)
		oldLogFunc.apply(console, arguments)
	}
		*/
}

/**
 * initialization of the settings menu
 */
export const menu = {
	func: "showSettingsInterface",
	icon: "fas fa-cog", // font awesome 5.11
	i8nIndex: "settings,uppercase",
	testClass: 'test-action-change-language'
}
