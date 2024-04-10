// Une fois tous les éléments chargés
window.addEventListener('load', (event) => {
  // uniquement pour raspberry pi
  if (SOCKET && glob.appConfig.periph === "FPI") {
    SOCKET.on('gerer_boutons', (retour) => {
      sys.logJson('retour = ', retour)

      // émule un clique
      if (retour.action === 'click_bouton') {
        console.log('-> clique article, selecteur = ' + retour.selecteur)
        document.querySelector(retour.selecteur).click()
      }

    })
  }
})
