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
