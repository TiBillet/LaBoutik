export default function () {
  let pv = glob.data.filter(obj => obj.service_direct === true)[0]
  let name = pv.name

  Test.titre(`Test simu retour POST "CHECK CARTE", OK, 0 monnaie !`)

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
    "code": 200,
    "texte": "OK"
  }
  let retour = {
    "tag_id": "7708A1FD",
    "number": "qf7fd",
    "wallet": null,
    "total_monnaie": 0,
    "membre_name": "sauron",
    "cotisation_membre_a_jour": "A Jour 17-08-2021",
    "cotisation_membre_a_jour_booleen": true,
    "cartes_maitresses": [
      "sauron qf7fd"
    ],
    "assets": [
      {
        "monnaie_name": "Bisik Cadeau",
        "qty": 0
      },
      {
        "monnaie_name": "Bisik",
        "qty": 0
      }
    ],
    "route": "check_carte"
  }

  // fonction de callback à lancer "gererRetourPostCheckCarte"
  Test.apresFonction('gererRetourPostCheckCarte', async function(retour, status, donnees) {
    // test la présence des mots: nom et nom du membre
    Test.elementInclutLesMots({
      sujet: `L'identifiant carte`,
      selecteur: '#popup-cashless div[class="check-carte-ok-nom"]',
      mots: ['Nom', retour.membre_name ]
    })

    // test contenu du popup
    Test.textElementEgal({
      selecteur: '#popup-cashless div[class="check-carte-ok-cotisation"]',
      valeur: retour.cotisation_membre_a_jour
    })

    // test l'information total monnaie est affichée
    Test.elementInclutLesMots({
      selecteur: '#popup-cashless div[class="check-carte-ok-total-carte"]',
      mots: ['Sur', 'carte', ':', retour.total_monnaie],
      msgOk: `- L'info. du total carte est correcte !`,
      msgEr: `. L'info. du total carte est incorrecte !`
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