export default async function () {
  let pv = glob.data.filter(obj => obj.service_direct === true)[0]
  let name = pv.name
  let serviceDirect = pv.service_direct
  Test.titre(`Teste un point de ventes, "${name}", dont le mode service directe est égal à "true" (coché) !`)

    // cliquer sur menu "burger"
  Test.elementClique({selecteur: '.menu-burger-icon'})

  // cliquer sur menu "POINTS DE VENTES"
  Test.elementClique({selecteur: '#menu-burger-conteneur .menu-burger-item[onclick="vue_pv.afficherMenuPV()"]'})

  // clique sur le point de ventes
  Test.elementClique({selecteur: `#menu-burger-conteneur div[class~="test-${name.toLowerCase()}"`})

  // attendre l'affichage de la vue
  let attente = await Test.elementAttendreAffichage({
    dureeMaxiAttente: 10000,
    selecteur: `#page-commandes`,
    msg: `Attendre(10 secondes maxi) l'affichage des articles !`,
  })

  // vue point de ventes affichées
  let affPV = document.querySelector(`#products div[data-name-pdv="${ name }"]`).style.display
  if (affPV === 'block') {
    Test.enregistrerErreur(false, `- La vue du point de vente est affichée !`)
  } else {
    Test.enregistrerErreur(true, `. La vue du point de vente n'est pas affichée !`)
  }

  // le bouton reset est présent
  Test.elementExiste({
    selecteur: '#page-commandes-footer div[class~="test-reset"]',
    msgOk: '- Le bouton RESET est présent !',
    msgEr: `. Le bouton RESET n'est pas présent !`
  })

  // le bouton check carte est présent
  Test.elementExiste({
    selecteur: '#page-commandes-footer div[class~="test-check-carte"]',
    msgOk: '- Le bouton CHECK CARTE est présent !',
    msgEr: `. Le bouton CHECK CARTE n'est pas présent !`
  })

  // le bouton valider est présent
  Test.elementExiste({
    selecteur: '#bt-valider',
    msgOk: '- Le bouton VALIDER TOTAL est présent !',
    msgEr: `. Le bouton VALIDER TOTAL n'est pas présent !`
  })

  Test.afficherBlockslogs()
}