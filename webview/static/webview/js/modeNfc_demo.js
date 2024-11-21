let SOCKET = null

// ajout des données démo (simulation lecetur nfc)
let Nfc = class {
  etatLecteurNfcInit = {
    message: '',
    callbackOk: null,
    data: {},
    uuidConnexion: '1b4dd191-6170-4677-935c-3ba23f9d5d05',
    demoTagIdCm: window.DEMO.demoTagIdCm,
    demoTagIdClient1: window.DEMO.demoTagIdClient1,
    demoTagIdClient2: window.DEMO.demoTagIdClient2,
    demoTagIdClient3: window.DEMO.demoTagIdClient3,
    tagIdIdentite: '',
    demoTagIdTempsReponse: window.DEMO.demoTagIdTempsReponse, // secondes
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

  verificationTagId(tagId, uuidConnexion) {
    let msgErreurs = 0, data

    window.clearTimeout(this.etatLecteurNfc.demoTempsActionTimeoutID)

    // mettre tagId en majuscule
    tagId = tagId.toUpperCase()

    // vérifier taille tagId
    let tailleTagId = tagId.length
    if (tailleTagId < 8 || tailleTagId > 8) {
      msgErreurs++
      sys.log('Erreur, taille tagId = ' + tailleTagId + ' !!')
    }

    // fixe le tagId à 'erreur'
    if (msgErreurs !== 0) {
      tagId = 'erreur'
    }

    // sys.log('-> verificationTagId, tagId = ' + tagId + ' uuidConnexion = ' + uuidConnexion)

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
    // console.log('-> lireTagId demo., this.etatLecteurNfc =', this.etatLecteurNfc)

    // compose le message à afficher
    let message = `<div id="popup-lecteur-nfc" class="BF-col">
      <fieldset style="margin-bottom: 1rem;">
        <legend data-i8n="nfcCardSimulation,capitalize">Simulation carte nfc</legend>
        <div class="BF-ligne-deb">
          <input type="radio" id="nfc-primaire" name="simu-tag-id" value="${DEMO.demoTagIdCm}">
          <label for="nfc-primaire" class="simu-carte" data-i8n="primary,capitalize">primaire</label>
        </div>
        <div class="BF-ligne-deb">
          <input type="radio" id="nfc-client1" name="simu-tag-id" value="${DEMO.demoTagIdClient1}">
          <label for="nfc-client1" class="simu-carte">Client 1</label>
        </div>
        <div class="BF-ligne-deb">
          <input type="radio" id="nfc-client2" name="simu-tag-id" value="${DEMO.demoTagIdClient2}">
          <label for="nfc-client2" class="simu-carte">Client 2</label>
        </div>
        <div class="BF-ligne-deb">
          <input type="radio" id="nfc-client3" name="simu-tag-id" value="${DEMO.demoTagIdClient3}">
          <label for="nfc-client3" class="simu-carte">Client 3</label>
        </div>
        <div class="BF-ligne-deb">
          <input type="radio" id="nfc-unknown" name="simu-tag-id" value="${DEMO.demoTagIdUnknown}">
          <label for="nfc-unknown" class="simu-carte" data-i8n="unknown, capitalize">inconnue</label>
        </div>
      </fieldset>
      ${this.etatLecteurNfc.message}
    </div>
    <style>
      .simu-carte:hover {
        color: #339448;
      }
    </style>`

    let bouton = ''
    // compose le bouton retour à afficher
    if (this.etatLecteurNfc.tagIdIdentite !== 'cm') {
      bouton += `<div class="popup-conteneur-bt-retour BF-col">
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="rfid.annuleLireTagId();fn.popupAnnuler();"></bouton-basique>
      </div>`
    }
    // - Afficher le message
    fn.popup({
      message: message,
      type: 'normal',
      boutons: bouton
    })

    // 1 - générer un uuidConnexion
    const uuidConnexion = sys.uuidV4()
    // renseigner la fonction de lecture du tagID du uuidConnexion
    this.muteEtat('uuidConnexion', uuidConnexion)

    // affectation fonction
    const ids = ['#nfc-primaire', '#nfc-client1', '#nfc-client2', '#nfc-client3', '#nfc-unknown']
    ids.forEach((id) => {
      document.querySelector(id).addEventListener('click', (event) => {
        this.verificationTagId(event.target.value, this.etatLecteurNfc.uuidConnexion)
      })
    })
  }

  annuleLireTagId() {
    // console.log('-> annuleLireTagId', new Date())
    window.clearTimeout(this.etatLecteurNfc.demoTempsActionTimeoutID)
  }

  /**
   * Initialise le mode de lecture nfc en mode simulation:
   */
  initModeLectureNfc() {
    // TODO: émettre un log "Simulation lecteur nfc"
    sys.log('-> Simulation lecteur nfc !')

    window.glob['appConfig'] = {
      hostname: "appareilDemo",
      password: "passwordDemo",
      front_type: "FOR",
      locale: "fr",
      mode_nfc: "modeNfcDemo",
      ip_lan: "127.0.0.1",
      pin_code: 123456
    }
    // console.log('-> initModeLectureNfc, glob.appConfig =', glob.appConfig, '  --  DEMO =', DEMO)
  }
}