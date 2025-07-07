// https://github.com/nerdy-harry/phonegap-nfc-api31?tab=readme-ov-file#nfcshowsettings

let NfcReader = class {
  constructor(options) {
    this.modeNfc = ''
    this.uuidConnexion = null
    this.socket = null
    this.socketUrl = options?.socketUrl
    this.socketPort = options?.socketPort
    this.intervalIDVerifApiCordova = null
    this.simuData = [
      { name: 'primaire', tagId: window?.DEMO?.demoTagIdCm },
      { name: 'client1', tagId: window?.DEMO?.demoTagIdClient1 },
      { name: 'client2', tagId: window?.DEMO?.demoTagIdClient2 },
      { name: 'client3', tagId: window?.DEMO?.demoTagIdClient3 },
      { name: 'unknown', tagId: 'XXXXXXXX' }
    ]
  }

  verificationTagId(tagId, uuidConnexion) {
    let msgErreurs = 0, data

    // mettre tagId en majuscule
    if (tagId !== null) {
      tagId = tagId.toUpperCase()

      // vérifier taille tagId
      let tailleTagId = tagId.length
      if (tailleTagId < 8 || tailleTagId > 8) {
        msgErreurs++
        console.log('Erreur, taille tagId = ' + tailleTagId + ' !!')
      }

      // vérifier uuidConnexion
      if (uuidConnexion !== this.uuidConnexion) {
        msgErreurs++
        console.log('Erreur uuidConnexion différent !!')
      }

      // fixe le tagId à 'erreur'
      if (msgErreurs !== 0) {
        tagId = 'erreur'
      }

      // récupération des data enregistrés lors de la demande de lecture
      data = this.etatLecteurNfc.data
      data.tagId = tagId

      // réinitialisation de l'état du lecteur nfc
      this.uuidConnexion = null

      // envoyer le résultat du lecteur
      const event = new CustomEvent("nfcResult", { detail: data })
      document.body.dispatchEvent(event)
    }
  }

  initCordovaNfc() {
    // console.log('-> initCordovaNfc,', new Date())
    try {

      nfc.addTagDiscoveredListener((nfcEvent) => {
        let tag = nfcEvent.tag
        sys.log('tagId = ' + nfc.bytesToHexString(tag.id))
        if (this.etatLecteurNfc.cordovaLecture === true) {
          this.verificationTagId(nfc.bytesToHexString(tag.id), this.etatLecteurNfc.uuidConnexion)
        }
      })
      clearInterval(this.intervalIDVerifApiCordova)
    } catch (error) {
      console.log('-> initCordovaNfc :', error)
    }
  }

  simule() {
    // compose le message à afficher
    let message = `<div id="nfc-reader-simu">
      <fieldset style="margin-bottom: 1rem;">
        <legend data-i8n="nfcCardSimulation,capitalize">Nfc - Simulation</legend>`

    this.simuData.forEach(item => {
      message += `
        <div class="nfc-reader-simu-ligne">
          <input type="radio" name="simu-tag-id" value="${item.tagId}">
          <label for="nfc-primaire" class="simu-carte">${item.name}</label>
        </div>
      `
    })

    message += `
      </fieldset>
    </div>
    <style>
      .nfc-reader-simu-ligne {
		    display: flex;
		    flex-direction: row;
		    justify-content: flex-start;
		    align-items: center;
	    }

      .simu-carte:hover {
        color: #339448;
      }
    </style>`
  }

  /**
  * Gestion de la réception du tagIDS et de l'uuidConnexion
  * @param mode
  */
  gestionModeLectureNfc(mode) {
    // console.log('-> gestionModeLectureNfc, mode =', mode)
    this.uuidConnexion = crypto.randomUUID()

    if (window.DEMO === undefined) {
      // nfc serveur socket_io + front sur le même appareil (pi ou desktop)
      if (mode === 'NFCLO') {
        // initialise la connexion
        this.socket = io(this.socketUrl + ':' + this.socketPort, {})

        // initialise la réception d'un tagId, méssage = 'envoieTagId'
        this.socket.on('envoieTagId', (retour) => {
          this.verificationTagId(retour.tagId, retour.uuidConnexion)
        })

        // initialise la getion des erreurs socket.io
        this.socket.on('connect_error', (error) => {
          // TODO: émettre un log
          console.error(`Socket.io - ${this.socketUrl}:${this.socketPort} :`, error)
        })

        // demande la lecture
        this.socket.emit('demandeTagId', { uuidConnexion: this.uuidConnexion })
      }

      // cordova
      if (mode === 'NFCMC') {
        this.intervalIDVerifApiCordova = setInterval(() => {
          this.initCordovaNfc()
        }, 500)
      }
    } else {
      simule()
    }
  }

  startLecture() {
    // récupère le nfcMode
    let modeNfc = '', infosNavigateur = null
    try {
      const storage = JSON.parse(localStorage.getItem('laboutik'))
      this.modeNfc = storage.mode_nfc
      this.gestionModeLectureNfc(modeNfc)
    } catch (err) {
      console.log(`Nfc initLecture, storage: ${err}  !`)
    }
  }

  stopLecture() {
    let modeNfc = this.modeNfc
    let uuidConnexion = this.etatLecteurNfc.uuidConnexion

    // tagId pour "un serveur nfc + front" en local
    if (modeNfc === "NFCLO") {
      // console.log('-> émettre: "AnnuleDemandeTagId"')
      this.socket.emit('AnnuleDemandeTagId', { uuidConnexion: this.uuidConnexion })
    }

    // cordova
    if (modeNfc === 'NFCMC') {
      clearInterval(this.intervalIDVerifApiCordova)
    }
  }
}