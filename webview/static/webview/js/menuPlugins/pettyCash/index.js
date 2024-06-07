/* scope global des fonctions:
    window.functionName = function () {
        .......
    }
*/

window.pettyCashAction = function () {
  // console.log("-> pettyCashAction !")
  // récupération de la valeur entrée
  const value = parseFloat(document.querySelector('#petty-cash').value)
  if (isNaN(value)) {
    document.querySelector('#petty-cash-msg-erreur').innerHTML = `<span data-i8n="isNotNumber,capitalize" style="color: red;">Ce n'est pas un nombre</span>`
  } else {
    const pettyCashValue = (new Big(value)).valueOf()

    // supression du popup
    fn.popupAnnuler()
  }
}

window.pettyCashInterface = function () {
  // console.log('-> fond de caisse / pettyCash')
  // efface le menu
  document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
  // popup de confirmation
  let message = `
   <div id="popup-cashless-confirm" class="BF-col popup-cashless-confirm-conteneur">
    <div class="BF-col" style="margin: 0 2%;">`

  // Sans clavier virtuel pour les autres fronts
  if (glob.appConfig.periph !== 'FPI') {
    message += `
        <input type="number" id="petty-cash" class="addition-fractionnee-input">
        <small id="petty-cash-msg-erreur"></small>
      `
  } else {
    // Avec clavier virtuel pour raspberry pi
    message += `
      <input id="petty-cash" class="addition-fractionnee-input" onclick="clavierVirtuel.obtPosition('petty-cash');clavierVirtuel.afficher('petty-cash','numSolo')">
      <small id="petty-cash-msg-erreur"></small>
    `
  }
  message += `</div>
    <div class="BF-ligne-entre">
      <bouton-basique id="popup-confirme-retour" traiter-texte="1" texte="RETOUR|1.5rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2rem" width="240px" height="100px"  onclick="fn.popupAnnuler();" style="margin: 8px"></bouton-basique>
      <bouton-basique id="popup-confirme-valider" traiter-texte="1" texte="VALIDER|1.5rem||validate-uppercase" couleur-fond="#339448" icon="fa-check-circle||2rem" width="240px" height="100px"  onclick="pettyCashAction();" style="margin: 8px;"></bouton-basique>
    </div>
   </div>
  `
  let options = {
    titre: '<h1 data-i8n="cashFloat,capitalize">Fond de caisse</h1>',
    message: message,
    type: 'normal'
  }
  fn.popup(options)
}

export const menu = {
  func: "pettyCashInterface",
  icon: "fas fa-cash-register", // font awesome 5
  i8nIndex: "cashFloat,uppercase"
}
