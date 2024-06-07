// Cloturation de toutes les casisses
// administration/views.py method "Close_all_pos"
window.closeAccounts = function () {
  // console.log('-> closeAccounts')
  const url = `${location.protocol}//${location.host}/close_all_pos`
  let csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value
  let requete = {
    type: 'get',
    url: 'close_all_pos/',
    dataTypeReturn: 'json',
    csrfToken: csrfToken,
    attente: {
      largeur: 160,
      couleur: '#FFFFFF',
      nbc: 10,
      rpt: 10,
      epaisseur: 20
    }
  }
  // sys.logJson('requete = ', requete)
  sys.ajax(requete, (retour, status) => {
    // sys.logJson('status = ', status)
    // sys.logJson('retour = ', retour)

    let typeMessage
    if (status.code >= 200 && status.constructor < 300) {
      typeMessage = 'succes'
    } else {
      typeMessage = 'retour'
    }
    if (status.code >= 400 && status.constructor < 600) {
      typeMessage = 'danger'
    }
    // TODO: envoyer un index de traduction (voir .../webview/static/webview/js/modules/i8n.js )
    // exemple: <h1 data-i8n="${retour.translateIndex}" style="white-space: pre-line; text-align: center;"></h1>
    const message = `<div style="margin: 0 2%;">
      <h1 data-i8n="${retour.translateIndex}" style="white-space: pre-line; text-align: center;">${retour.message}</h1>
    </div>`
    const bouton = `<div class="popup-conteneur-bt-retour BF-col">
      <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#0a2e64" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="fn.popupAnnuler();"></bouton-basique>
    </div>`
    const options = {
      titre: message,
      boutons: bouton,
      type: typeMessage
    }
    fn.popup(options)
  })
}


// Confirmation pour "Cloturer toutes les caisses"
window.closeAccountsConfirmation = function () {
  // console.log('-> closeAccountsConfirmation')
  // efface le menu
  document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
  // popup de confirmation
  let message = `
     <div id="popup-cashless-confirm" class="BF-col popup-cashless-confirm-conteneur">
      <div class="BF-col" style="margin: 0 2%;">
        <h1 data-i8n="confirmClosureCrates,capitalize" style="white-space: pre-line; text-align: center;">
          Confirmez la cloture des caisses.
          </h1>
        <h1 data-i8n="onceValidatedNoReturn,capitalize" style="white-space: pre-line; text-align: center;">
          Attention, une fois validé, aucun retour possible!
        </h1>
      </div>
      <div class="BF-ligne-entre">
        <bouton-basique id="popup-confirme-retour" traiter-texte="1" texte="RETOUR|1.5rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2rem" width="240px" height="100px"  onclick="fn.popupAnnuler();" style="margin: 8px"></bouton-basique>
        <bouton-basique id="popup-confirme-valider" traiter-texte="1" texte="VALIDER|1.5rem||validate-uppercase" couleur-fond="#339448" icon="fa-check-circle||2rem" width="240px" height="100px"  onclick="fn.popupAnnuler();closeAccounts();" style="margin: 8px;"></bouton-basique>
      </div>
     </div>
    `
  let options = {
    message: message,
    type: 'normal'
  }
  fn.popup(options)
}


export const menu = {
  func: "closeAccountsConfirmation",
  icons: [
    { icon: "fas fa-cash-register", size: 1.2, posX: '8px', posY: '10px'},
    { icon:"fas fa-ban", size: 2.4, false: true, color: "#ff0000"}
  ],
  // i8nIndex: "closeAccounts,uppercase"
  i8nIndex: "closeCashRegister,uppercase"
}
