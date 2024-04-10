export default function () {
  let pv = glob.data.filter(obj => obj.service_direct === true)[0]
  let name = pv.name

  Test.titre(`Test simu retour POST "CHECK CARTE", carte inconnue (404) !`)

  // cliquer sur menu "burger"
  Test.elementClique({ selecteur: '.menu-burger-icon'})

  // cliquer sur menu "POINTS DE VENTES"
  Test.elementClique({ selecteur: '#menu-burger-conteneur .menu-burger-item[onclick="vue_pv.afficherMenuPV()"]'})

  // clique sur le point de ventes
  Test.elementClique({ selecteur: `#menu-burger-conteneur div[class~="test-${name.toLowerCase()}"`})

  // données pour la simulation, status 404
  let status = {
    "code": 404,
    "texte": "Not Found"
  }
  let retour = {
    "msg": "carte inconnue",
    "tag_id": "3930EB5E"
  }
  let donnees = {
    "typeCheckCarte": "parLecteurNfc",
    "tagId": "3930EB5E"
  }

  // fonction de callback à lancer "gererRetourPostCheckCarte"
  Test.apresFonction('gererRetourPostCheckCarte', async function(retour, status, donnees) {
    // test couleur du fond
    Test.elementStyleEgale({
      selecteur: '#popup-cashless',
      typeStyle: 'background-color',
      valeur: 'rgb(184, 85, 33)'
    })

    // info. affichée "Carte inconnue"
    Test.textElementEgal({
      selecteur: '#popup-cashless div div',
      valeur: 'carte inconnue', // la capitalisation n'est pas prise en compte(donnée brute en minuscule)
      msgOk: `- Le texte "Carte inconnue" est bien affiché sur le popup !`,
      msgEr: `. Le texte "Carte inconnue" n'est pas affiché sur le popup !`
    })
  })
  gererRetourPostCheckCarte(retour, status, donnees)

  // le bouton RETOUR est présent
  Test.elementExiste({
    selecteur: '#popup-retour',
    msgOk: '- Le bouton RETOUR est présent !',
    msgEr: `. Le bouton RETOUR n'est pas présent !`
  })

  // Actions du bouton retour "Attente lecture carte"
  Test.elementFonctionCliqueEgale({
    selecteur: '#popup-retour',
    valeur: `fn.popupAnnuler();`
  })

  // cliquer sur menu "RETOUR"
  Test.elementClique({
    selecteur: '#popup-retour',
    msg: `Bouton Retour Cliqué !`
  })

  // le popup doit être effacé
  Test.elementExistePas({
    selecteur: '#popup-cashless',
    msgOk: '- Le popup est bien effacé !',
    msgEr: `. Le popup n'est pas effacé !`
  })

  Test.afficherBlockslogs()
}