window.changeLanguageAction = function () {
  console.log("-> changeLanguageAction !")
  // récupération de la valeur entrée
  const selectLanguage = document.querySelector('input[type="radio"][name="select-language"]:checked').value
  // console.log('selectLanguage =', selectLanguage)
  localStorage.setItem("language", selectLanguage)
  // TODO: infomer le serveur du changement de langue
  vue_pv.reloadData()
}

window.changeLanguageInterface = function () {
  const local = localStorage.getItem("language")
  const data = getLanguages()

  // efface le menu
  document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
  // popup de confirmation
  let message = `<div class="BF-col popup-cashless-confirm-conteneur">
    <h1 data-i8n="selectLanguage,capitalize" style="color: #ffffff; margin-bottom: 4px;">Sélectionner une langue</h1>
    <h2 style="margin-top: 0; margin-bottom: 2rem">L'application sera rechargée.</h2>
    <div class="BF-col" style="margin: 0 4rem;">`

  for (let i = 0; i < data.length; i++) {
    const langue = data[i].language
    const label = data[i].infos

    if (langue === local) {
      message += `<div style="margin-bottom: 3rem;">
        <input type="radio" id="language-${i}" name="select-language" value="${langue}" checked />
        <label for="language-${i}">${label}</label>
      </div>`
    } else {
      message += `<div style="margin-bottom: 3rem;">
        <input type="radio" id="language-${i}" name="select-language" value="${langue}" />
        <label for="language-${i}">${label}</label>
      </div>`
    }

  }
  message += `</div>
  <div class="BF-ligne-entre">
    <bouton-basique id="popup-confirme-retour" traiter-texte="1" texte="RETOUR|1.5rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2rem" width="240px" height="100px"  onclick="fn.popupAnnuler();" style="margin: 8px"></bouton-basique>
    <bouton-basique id="popup-confirme-valider" traiter-texte="1" texte="VALIDER|1.5rem||validate-uppercase" couleur-fond="#339448" icon="fa-check-circle||2rem" width="240px" height="100px"  onclick="changeLanguageAction();" style="margin: 8px;"></bouton-basique>
  </div>
  </div>`

  const boutons = ` `

  let options = {
    message: message,
    type: 'normal'
  }
  fn.popup(options)
  console.log('langues =', data)
}

export const menu = {
  func: "changeLanguageInterface",
  icon: "fas fa-globe", // font awesome 5.11
  i8nIndex: "language,uppercase"
}
