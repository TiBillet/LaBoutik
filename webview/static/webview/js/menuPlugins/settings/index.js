/**
 * List of the modules configuration of the settings item menu 
 * @type {Array<object>}
 */
window.settingsActions = [
	{ i8nIndex: 'infos', icon: 'fa-info', func: 'settingsShowInfos', moduleName: 'infos' },
	{ i8nIndex: 'language', icon: 'fa-language', func: 'settingsChangeLanguage', moduleName: 'language' },
	{ i8nIndex: 'logs', icon: 'fa-stethoscope', func: 'settingsShowLogs', moduleName: 'logs' },
	{ i8nIndex: 'printer', icon: 'fa-print', func: 'settingsShowPrinter', moduleName: 'printer', conditions: ['hasSunmiPrinter'] }
]

window.settinsLoadModule = async function (name) {
	await import("./" + name + '.js')
}

window.settingsLaunchAction = async function (ev) {
	const cible = ev.target
	const action = cible.classList.contains("target-settings") === true ? cible.getAttribute('action') : null

	if (action !== null) {
		try {
			// charge le module
			const actionConf = settingsActions.find(item => item.func === action)

			if (actionConf.moduleName && actionConf.load === undefined) {
				await settinsLoadModule(actionConf.moduleName)
				actionConf['load'] = true
			}

			if (window[action] !== undefined) {
				window[action]()
			}

			if (window[action] === undefined) {
				console.log(getTranslate('functionSettingsNotExist').replace('{replace}', action))
			}
		} catch (error) {
			console.log('-> settingsLaunchAction : no module or no function.')
		}
	}
}

/**
 * Show settings UI
 * @returns {void}
 */
window.showSettingsInterface = async function () {
	// efface le menu
	document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
	// éfface les autres élément(pages)
	sys.effacerElements(['#page-commandes', '#tables', '#commandes-table'])
	// rend visible l'élément(page) '#service-commandes'
	sys.afficherElements(['#service-commandes,block'])

	// changer titre
	// vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="${settingsActions[0].title},capitalize">Infos</span>`)

	const style = `
	<style>
	#service-commandes {
		--width-nav-settings: 20%;
		--height-bt-settings: 80px;
	}

	.nav-settings {
		width: var(--width-nav-settings);
		height: 100%;
		background-color: var(--bleu09);
		color: var(--blanc01);
		overflow-y: scroll;
		border-right: 1px solid var(--gris01);
	}

	.bt-settings {
		position: relative;
		width:100%;
		height: var(--height-bt-settings);
		border-bottom: 1px solid var(--gris01);
		margin: 4px 0;
	}

	.target-settings {
		position: absolute;
		left: 0;
		top: 0;
		width: 98%;
		height: var(--height-bt-settings);
		opacity: 0;
	}

	.content-settings {
		width: calc(100% - var(--width-nav-settings));
		height: 100%;
		background-color: var(--bleu09);
		color: var(--blanc01);
		overflow-y: scroll;
		padding: 6px;
	}
	</style>`

	let template = `
	<div class="BF-ligne l100p h100p">
		<div class="BF-col-deb nav-settings">`

	// settings navigation
	for (let i = 0; i < settingsActions.length; i++) {
		const action = settingsActions[i];
		let permission = true
		
		// permissions
		if (action.conditions !== undefined) {
			permission = await sys.testArrayPermissions(action.conditions)
		}

		if (permission === true) {
			template += `<div class="BF-col bt-settings">
			<i class="fas ${action.icon} mb4px"></i>
			<span>${getTranslate(action.i8nIndex, 'uppercase')}</span>
			<div class="target-settings" action="${action.func}"></div>
			</div>`
		}
	}

	template += `
		</div>
		<div class="BF-col-deb content-settings"></div>
	</div>`

	document.querySelector('#service-commandes').innerHTML = style + template

	// event listener
	document.querySelector('.nav-settings').addEventListener('click', settingsLaunchAction)

	await settinsLoadModule('infos')

	// show infos
	settingsShowInfos()
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
