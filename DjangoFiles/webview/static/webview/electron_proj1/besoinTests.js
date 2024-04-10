const TOKEN = '$a;b2yuM5454@4!cd'
let SOCKET = null

// ajout des données démo (simulation lecetur nfc)
let Nfc = class {
  etatLecteurNfcInit = {
    message: '',
    callbackOk: null,
    data: {},
    uuidConnexion: '1b4dd191-6170-4677-935c-3ba23f9d5d05',
    demoTagIdCm: '7708A1FD',
    demoTagIdClient1: '41726643',
    demoTagIdClient2: '52BE6543',
    tagIdIdentite: '',
    demoTagIdTempsReponse: 1, // secondes
    demoTempsActionTimeoutID: 0
  }

  etatLecteurNfc = this.etatLecteurNfcInit

  muteEtat(cible, don) {
    if (cible in this.etatLecteurNfc) {
      this.etatLecteurNfc[cible] = don
    } else {
      sys.log(cible + ' inconnue !')
    }
  }

  verificationTagId(tagId,uuidConnexion) {
    let msgErreurs = 0, data

    window.clearTimeout(this.etatLecteurNfc.demoTempsActionTimeoutID)

    // mettre tagId en majuscule
    tagId = tagId.toUpperCase()

    // vérifier taille tagId
    let tailleTagId = tagId.length
    if (tailleTagId < 8 || tailleTagId > 8) {
      msgErreurs ++
      sys.log('Erreur, taille tagId = ' + tailleTagId + ' !!')
    }

    // fixe le tagId à 'erreur'
    if (msgErreurs !== 0 ) {
      tagId = 'erreur'
    }

    sys.log('-> verificationTagId, tagId = ' + tagId + ' uuidConnexion = ' + uuidConnexion)

    // récupération des data enregistrés lors de la demande de lecture
    data = this.etatLecteurNfc.data
    data.tagId = tagId

    // réinitialisation de l'état du lecteur nfc
    this.etatLecteurNfc = this.etatLecteurNfcInit

    // effacer le popup "Attente lecture carte" et 'chargement ajax'
    fn.popupAnnuler()
    sys.affCharge({ etat: 0 })

    // lancer callback avec ses data
    this.etatLecteurNfc.callbackOk(data)
  }


  lireTagId() {
    let tagId = ''

    // compose le message à afficher
    let message = `
      <div id="popup-lecteur-nfc" class="BF-col">
        ${ this.etatLecteurNfc.message }
      </div>
    `;
    // compose le bouton retour à afficher
    let bouton = `
      <div class="popup-conteneur-bt-retour BF-col">
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem|" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="nfc.annuleLireTagId();fn.popupAnnuler();"></bouton-basique>
      </div>
    `
    // - Afficher le message
    fn.popup({
      message: message,
      type: 'normal',
      boutons: bouton
    })

    // ---- simulation réception tagId ----
    if (this.etatLecteurNfc.tagIdIdentite === 'cm') {
      tagId = this.etatLecteurNfc.demoTagIdCm
    }

    if (this.etatLecteurNfc.tagIdIdentite === 'client1') {
      tagId = this.etatLecteurNfc.demoTagIdClient1
    }

    if (this.etatLecteurNfc.tagIdIdentite === 'client2') {
      tagId = this.etatLecteurNfc.demoTagIdClient2
    }

    // TODO: émettre un log
    sys.log('-> tagId simulé  = ' + tagId)

    // délais pour visualiser le message de retour
    sys.affCharge({etat: 1, largeur: 80, couleur: '#0F0', nbc: 8, rpt: 4, epaisseur: 8 })
    this.etatLecteurNfc.demoTempsActionTimeoutID = window.setTimeout(() => {
      this.verificationTagId(tagId, this.etatLecteurNfc.uuidConnexion)
    }, this.etatLecteurNfc.demoTagIdTempsReponse * 1000)
  }

  annuleLireTagId() {
    window.clearTimeout(this.etatLecteurNfc.demoTempsActionTimeoutID)
  }

  /**
   * Initialise le mode de lecture nfc en mode simulation:
   */
  initModeLectureNfc() {
    // TODO: émettre un log "Simulation lecteur nfc"
    sys.log('-> Simulation lecteur nfc !')
    glob.infosNavigateur = JSON.parse('{"hostname":"appareilDemo","password":"passwordDemo","modeNfc":"modeNfcDemo","front":"FOR","ip":"88.88.88.88"}')
    // sys.logJson('etatLecteurNfc = ', this.etatLecteurNfc)
  }
}