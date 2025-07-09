// https://github.com/nerdy-harry/phonegap-nfc-api31?tab=readme-ov-file#nfcshowsettings

let NfcReader = class {
  constructor() {
    this.modeNfc = ''
    this.uuidConnexion = null
    this.socket = null
    this.socketPort = 3000
    this.intervalIDVerifApiCordova = null
    this.cordovaLecture = false
    this.simuData = [
      { name: 'primary', tagId: window?.DEMO?.demoTagIdCm },
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

      // envoyer le résultat du lecteur
      if (msgErreurs === 0) {
        const event = new CustomEvent("nfcResult", { detail: tagId })
        document.body.dispatchEvent(event)

        // réinitialisation de l'état du lecteur nfc
        this.uuidConnexion = null
      }
    }
  }

  listenCordovaNfc() {
    console.log('-> listenCordovaNfc,', new Date())
    try {
      nfc.addTagDiscoveredListener((nfcEvent) => {
        let tag = nfcEvent.tag
        if (this.cordovaLecture === true) {
          this.verificationTagId(nfc.bytesToHexString(tag.id), this.uuidConnexion)
        }
      })
      clearInterval(this.intervalIDVerifApiCordova)
    } catch (error) {
      console.log('-> listenCordovaNfc :', error)
    }
  }

  simule() {
    // compose le message à afficher
    let uiSimu = `<div id="nfc-reader-simu-overlay">
      <fieldset id="nfc-reader-simu-container">
        <legend data-i8n="nfcCardSimulation,capitalize">Nfc - Simulation</legend>`

    this.simuData.forEach((item, i) => {
      uiSimu += `
        <div class="nfc-reader-simu-bt" tag-id="${item.tagId}">${item.name}</div>
      `
    })

    uiSimu += `
      </fieldset>
    </div>
    <style>
      #nfc-reader-simu-overlay {
        width: 100vw;
        height: 100vh;
        position: absolute;
        left: 0;
        top: 0;
        opacity: 0.9;
        display: flex;
		    flex-direction: column;
		    justify-content: center;
		    align-items: center;
        background-color:#000000;
      }

      #nfc-reader-simu-container {
        min-height: 200px;
        padding: 20px;
        background-color:rgba(255, 255, 255,1);
        color: #000000;
        opacity: 1;
        display: flex;
		    flex-direction: column;
		    justify-content: center;
		    align-items: center;
      }

      .nfc-reader-simu-bt {
        width: 150px;
        height: 80px;
        background-color: #0000ff;
        color: #ffffff;
		    display: flex;
		    flex-direction: row;
		    justify-content: center;
		    align-items: center;
        font-size: 1.5rem;
        margin-bottom: 2rem;
        border-radius: 8px;
        font-weight: bold;
	    }

      .nfc-reader-simu-ligne label {
        margin-left: 10px;
      }
    </style>`
    document.body.insertAdjacentHTML('beforeend', uiSimu)
    document.querySelectorAll('.nfc-reader-simu-bt').forEach((bt) => {
      bt.addEventListener('click', () => {
        const tagId = bt.getAttribute('tag-id')
        console.log('tagId =', tagId);

        // hide ui simu
        document.querySelector('#nfc-reader-simu-overlay').remove()

        // envoyer le résultat du lecteur
        const event = new CustomEvent("nfcResult", { detail: tagId })
        document.body.dispatchEvent(event)
      })
    })
  }

  /**
  * Gestion de la réception du tagIDS et de l'uuidConnexion
  * @param mode
  */
  gestionModeLectureNfc(mode) {
    // console.log('1 -> gestionModeLectureNfc, mode =', mode)
    this.uuidConnexion = crypto.randomUUID()

    // nfc serveur socket_io + front sur le même appareil (pi ou desktop)
    if (mode === 'NFCLO') {
      // initialise la connexion
      this.socket = io('http://localhost:' + this.socketPort, {})

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
      this.cordovaLecture = true
      this.intervalIDVerifApiCordova = setInterval(() => {
        this.listenCordovaNfc()
      }, 500)
    }
  }

  startLecture(options) {
    console.log('0 -> startLecture  --  DEMO =', window?.DEMO)
    // simule
    if (options?.simulation === true) {
      this.simule()
    } else {
      // hardware
      // récupère le nfcMode
      try {
        const storage = JSON.parse(localStorage.getItem('laboutik'))
        this.modeNfc = storage.mode_nfc
        this.gestionModeLectureNfc(this.modeNfc)
      } catch (err) {
        console.log(`Nfc initLecture, storage: ${err}  !`)
      }
    }
  }

  stopLecture() {
    console.log('1 -> stopLecture')
    let modeNfc = this.modeNfc

    // tagId pour "un serveur nfc + front" en local
    if (modeNfc === "NFCLO") {
      // console.log('-> émettre: "AnnuleDemandeTagId"')
      this.socket.emit('AnnuleDemandeTagId', { uuidConnexion: this.uuidConnexion })
    }

    // cordova
    if (modeNfc === 'NFCMC') {
      this.cordovaLecture = false
      clearInterval(this.intervalIDVerifApiCordova)
    }

    this.uuidConnexion = null
  }
}