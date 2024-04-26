export default function () {
  let pv = glob.data.filter(obj => obj.service_direct === true)[0]
  let name = pv.name

  Test.titre(`Test simu retour POST "CHECK CARTE",status 400 !`)

  // cliquer sur menu "burger"
  Test.elementClique({selecteur: '.menu-burger-icon'})

  // cliquer sur menu "POINTS DE VENTES"
  Test.elementClique({selecteur: '#menu-burger-conteneur .menu-burger-item[onclick="vue_pv.afficherMenuPV()"]'})

  // clique sur le point de ventes
  Test.elementClique({selecteur: `#menu-burger-conteneur div[class~="test-${name.toLowerCase()}"`})

  // données pour la simulation
  let donnees = {
    "typeCheckCarte": "parLecteurNfc",
    "tagId": "7708A1FD"
  }
  let status = {
    "code": 400,
    "texte": "text de l'erreur !"
  }
  let retour = {}

  // fonction de callback à lancer "gererRetourPostCheckCarte"
  Test.apresFonction('gererRetourPostCheckCarte', async function(retour, status, donnees) {
    // test couleur du fond
    Test.elementStyleEgale({
      selecteur: '#popup-cashless',
      typeStyle: 'background-color',
      valeur: 'rgb(114, 39, 39)'
    })

    // titre
    Test.textElementEgal({
      selecteur: '#popup-cashless .popup-titre1',
      valeur: `Erreur :`,
      msgOk: `- Le titre "Erreur :" est affiché !`,
      msgEr: `. Le titre "Erreur :" n'est pas affiché !`
    })

    // info
    Test.textElementEgal({
      selecteur: '#popup-cashless .popup-msg1',
      valeur: `après un check-carte !`,
      msgOk: `- La provenance de l'erreur est affichée !`,
      msgEr: `. La provenance de l'erreur n'est pas affichée !`
    })

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
  })
  gererRetourPostCheckCarte(retour, status, donnees)
}