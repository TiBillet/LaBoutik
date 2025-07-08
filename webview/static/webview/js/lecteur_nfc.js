// token pour serveur nfc  utilisé par le pi et desktop
let SOCKET = null, intervalIDVerifApiCordova, cp = 0
// port du serveur nfc  pour pi et desktop
let PORT = 3000

let Nfc = class {
  // état initial
  etatLecteurNfc = {
    message: '', // par défaut
    callbackOk: null,
    uuidConnexion: '',
    modeNfc: '',
    data: {},
    tagIdIdentite: '',
    cordovaLecture: false,
    options: {}
  }

  muteEtat(cible, don) {
    if (cible in this.etatLecteurNfc) {
      this.etatLecteurNfc[cible] = don
      // console.log('etatLecteurNfc  = ' + JSON.stringify(etatLecteurNfc, null, '\t'))
    } else {
      sys.log(cible + ' inconnue !')
    }
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
        // TODO: émettre un log
        sys.log('Erreur, taille tagId = ' + tailleTagId + ' !!')
      }

      // vérifier uuidConnexion
      if (uuidConnexion !== this.etatLecteurNfc.uuidConnexion) {
        msgErreurs++
        // TODO: émettre un log
        sys.log('Erreur uuidConnexion différent !!')
      }

      // fixe le tagId à 'erreur'
      if (msgErreurs !== 0) {
        tagId = 'erreur'
      }

      // TODO: émettre un log
      // sys.log('-> verificationTagId, tagId = ' + tagId + ' uuidConnexion = ' + uuidConnexion)

      // récupération des data enregistrés lors de la demande de lecture
      data = this.etatLecteurNfc.data
      data.tagId = tagId

      // réinitialisation de l'état du lecteur nfc
      this.etatLecteurNfc.uuidConnexion = ''
      this.etatLecteurNfc.cordovaLecture = false


      // effacer le popup "Attente lecture carte"
      fn.popupAnnuler()

      // lancer callback avec ses data
      this.etatLecteurNfc.callbackOk(data)
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
      },
        function () {
          sys.log("Lecture tag id: OK!")
        },
        function () {
          sys.log("Lecture tag id:  Erreur!")
        })
      clearInterval(intervalIDVerifApiCordova)

    } catch (e) {
      sys.log(cp + ' -> nfc indéfini, réessayer !')
    }

  }

  /**
   * Gestion de la réception du tagIDS et de l'uuidConnexion
   * @param mode
   */
  gestionModeLectureNfc(mode) {
    // console.log('-> gestionModeLectureNfc, mode =', mode)
    // nfc serveur socket_io + front sur le même appareil (pi ou desktop)
    if (mode === 'NFCLO') {
      // initialise la connexion
      SOCKET = io('http://localhost:' + PORT, {})

      // initialise la réception d'un tagId, méssage = 'envoieTagId'
      SOCKET.on('envoieTagId', (retour) => {
        // sys.logJson('retour serveur nfc : ', retour)
        this.verificationTagId(retour.tagId, retour.uuidConnexion)
      })

      // initialise la getion des erreurs socket.io
      SOCKET.on('connect_error', (error) => {
        // TODO: émettre un log
        console.error('Socket.io : ', error)
      })
    }

    // lecture nfc hardware interne/mobile(jav)
    if (mode === 'NFCMO') {
      // TODO: émettre un log
      // console.log('L\'initailsation du mode nfc "NFCMO" se fera lors de la lecture du tagId !')
    }

    // cordova
    if (mode === 'NFCMC') {
      intervalIDVerifApiCordova = setInterval(() => {
        this.initCordovaNfc()
      }, 500)
    }

  }

  /**
   * Initialise le mode de lecture nfc en fonction du user-agent:
   * - NFCLO = serveur websocket(socket.io)/nfc local (Front+serveur nfc sur même machine), par défaut
   * - NFCDE = serveur websocket(socket.io)/nfc déporté/distant
   * - NFCMO = lecture nfc hardware interne/mobile
   * - NFCSI = simulation d'un lecteur nfc de type interne/mobile
   */
  initModeLectureNfc() {
    // récupère le nfcMode
    let modeNfc = '', infosNavigateur = null
    try {
      const storage = JSON.parse(localStorage.getItem('laboutik'))
      modeNfc = storage.mode_nfc
      // console.log('lecteur_nfc.js, modeNfc =', modeNfc)
    } catch (err) {
      sys.log(`storage -> ${err}  !`)
    }

    // TODO: émettre un log (convertir "modeNfc" et "infosNavigateur.front" en plus "humain")
    // console.log('modeNfc : ' + modeNfc + ', type front : ' +glob.appConfig.mode_nfc)

    this.muteEtat('modeNfc', modeNfc)
    this.gestionModeLectureNfc(modeNfc)
  }

  lireTagId() {
    let modeNfc = this.etatLecteurNfc.modeNfc
    // console.log('-> lireTagId, modeNfc =', modeNfc)
    // 1 - générer un uuidConnexion
    const uuidConnexion = crypto.randomUUID()

    // TODO: émettre un log
    // console.log('uuidConnexion : ' + uuidConnexion)
    // renseigner la fonction de lecture du tagID du uuidConnexion
    this.muteEtat('uuidConnexion', uuidConnexion)

    // compose le message à afficher
    let message = `
      <div id="popup-lecteur-nfc" class="BF-col">
        ${this.etatLecteurNfc.message}
      </div>
    `

    // compose le bouton retour à afficher
    let bouton = ''
    let addFunctions = ''
    // console.log('tes add funcs =', this.etatLecteurNfc.options.addFunctions)
    if (this.etatLecteurNfc.options.addFunctionsToBtReturn !== undefined) {
      addFunctions = this.etatLecteurNfc.options.addFunctionsToBtReturn
    }
    if (this.etatLecteurNfc.tagIdIdentite !== 'cm') {
      bouton = `<div class="popup-conteneur-bt-retour BF-col">
        <bouton-basique id="popup-retour" traiter-texte="1" texte="RETOUR|2rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2.5rem" width="400px" height="120px"  onclick="rfid.annuleLireTagId();fn.popupAnnuler();${addFunctions}"></bouton-basique>
      </div>`
    }

    // 2 - Afficher le message
    fn.popup({
      message: message,
      type: 'normal',
      boutons: bouton
    })

    // 3 ---- demande la lecture du tagId ----

    // tagId pour "un serveur nfc + front" en local (socket.io)
    if (modeNfc === "NFCLO") {
      SOCKET.emit('demandeTagId', { uuidConnexion: uuidConnexion })
      // TODO: émettre un log
      // console.log('Front - SOCKET.emit : demandeTagId .')
    }

    // tagId pour hardware interne/mobile(java)
    if (modeNfc === 'NFCMO') {
      // initialise  la passerelle javascript/java
      glob.NFC_INTERNAL_READER = {
        tagId: 'null',
        uuidConnexion: uuidConnexion, // renseigne java
        annuleLecture: 0
      }

      try {
        // TODO: émettre un log
        // console.log('Front - Android.jsCallback  = demande TagId .')
        // demande à java la lecture du tag id (lecetur nfc intégré du mobile )
        Android.jsCallback()

        // initialise le uuidConnexion à 'null'
        glob.NFC_INTERNAL_READER.uuidConnexion = 'null'

        // tester que glob.NFC_INTERNAL_READER.tagId !== 'null' à interval donné
        // let tc = 0 // test dev
        const fn_lecture_valeur_nfc = window.setInterval(() => { // itérations
          // valeur du tagId
          let tagId = glob.NFC_INTERNAL_READER.tagId
          // test dev
          // console.log(tc + ' ->' + tagId + '<-  --  type = ' + typeof tagId)

          // annule la lecture du tagId si demmande faite
          if (glob.NFC_INTERNAL_READER.annuleLecture === 1 || (glob.NFC_INTERNAL_READER.annuleLecture === 0 && tagId !== 'null')) {
            // fin de test: glob.NFC_INTERNAL_READER.tagId !== 'null'
            window.clearInterval(fn_lecture_valeur_nfc)
            glob.NFC_INTERNAL_READER.tagId = 'null'
            // réactivation pour prochaine lecture
            glob.NFC_INTERNAL_READER.annuleLecture = 0
          }

          // réceptionne le tagId
          if (glob.NFC_INTERNAL_READER.annuleLecture === 0 && tagId !== 'null') {
            this.verificationTagId(tagId, glob.NFC_INTERNAL_READER.uuidConnexion)
          }

          // tc++ // test dev
        }, 500)

      } catch (error) {
        // TODO: émettre un log
        console.log(" -> Objet Android : " + error)
        // TODO: afficher le méssage si-dessus sur l'écran
      }
    }

    // tagId pour hardware interne/mobile(cordova)
    if (modeNfc === 'NFCMC') {
      this.muteEtat('cordovaLecture', true)
    }

  }

  annuleLireTagId() {
    let modeNfc = this.etatLecteurNfc.modeNfc
    let uuidConnexion = this.etatLecteurNfc.uuidConnexion

    // tagId pour "un serveur nfc + front" en local
    if (modeNfc === "NFCLO") {
      // console.log('-> émettre: "AnnuleDemandeTagId"')
      SOCKET.emit('AnnuleDemandeTagId', { uuidConnexion: uuidConnexion })
    }

    // tagId pour hardware interne/mobile
    if (modeNfc === 'NFCMO') {
      glob.NFC_INTERNAL_READER.annuleLecture = 1
    }

    if (modeNfc === 'NFCMC') {
      this.muteEtat('cordovaLecture', false)
    }
  }

}
