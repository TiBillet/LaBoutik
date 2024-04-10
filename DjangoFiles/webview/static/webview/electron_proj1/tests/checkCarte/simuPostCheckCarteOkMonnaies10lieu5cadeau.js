export default function () {
  let pv = glob.data.filter(obj => obj.service_direct === true)[0]
  let name = pv.name

  Test.titre(`Test simu retour POST "CHECK CARTE", OK, monnaies: 10(lieu) et 5(cadeau) !`)

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
    "total_monnaie": 15,
    "membre_name": "sauron",
    "cotisation_membre_a_jour": "A Jour 17-08-2021",
    "cotisation_membre_a_jour_booleen": true,
    "cartes_maitresses": [
      "sauron qf7fd"
    ],
    "assets": [
      {
        "monnaie_name": "Bisik Cadeau",
        "qty": 5
      },
      {
        "monnaie_name": "Bisik",
        "qty": 10
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
      valeur: retour.cotisation_membre_a_jour,
      msgOk: `- Le texte "${ retour.cotisation_membre_a_jour }" est bien affiché sur le popup !`,
      msgEr: `. Le texte "${ retour.cotisation_membre_a_jour }" n'est pas affiché sur le popup !`
    })

    // test l'information total monnaie est affichée
    Test.elementInclutLesMots({
      selecteur: '#popup-cashless div[class="check-carte-ok-total-carte"]',
      mots: ['Sur', 'carte', ':', retour.total_monnaie],
      msgOk: `- L'info. du total carte est correcte !`,
      msgEr: `. L'info. du total carte est incorrecte !`
    })

    // récupère les informations(assets/monnaies) du front
    let elementsFront = document.querySelectorAll('#popup-cashless .test-item-monnaie')
    let tabElementsFront = []
    for (let i = 0; i < elementsFront.length; i++) {
      let element = elementsFront[i]
      let elementNom = elementsFront[i].querySelector('.test-nom-monnaie').innerHTML
      let elementValeur = parseFloat(elementsFront[i].querySelector('.test-valeur-monnaie').innerHTML)
      tabElementsFront.push(`${ elementNom },${ elementValeur }`)
    }
    let testTabElementsFront = JSON.stringify(tabElementsFront)
    // récupère les données de retour serveur
    let assets = retour.assets
    let tabDonneesServeur = []
    for (let i = 0; i < assets.length; i++) {
      let valeurAsset = parseFloat(assets[i].qty)
      let nomAsset = assets[i].monnaie_name
      tabDonneesServeur.push(`${ nomAsset },${ valeurAsset }`)
    }
    let testTabDonneesServeur = JSON.stringify(tabDonneesServeur)
    // test l'égalité des données
    if (testTabElementsFront === testTabDonneesServeur){
      Test.enregistrerErreur(false, '- Les informations du portefeuilles sont correctes !' )
    } else {
      Test.enregistrerErreur(true, '. Les informations du portefeuilles sont incorrectes !' )
    }

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