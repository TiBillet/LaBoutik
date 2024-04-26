// Etendre la class rfid afin d'émuler la lecture d'une carte
class emuleNfc extends Nfc {
  constructor(length) {
    super(length, length)
    this.name = 'simuNfc'
  }

  emulerLecture(valeur) {
    // annule la lecture du côté serveur nfc
    this.annuleLireTagId()
    // emule la lecture d'un tagId
    this.verificationTagId(valeur, this.etatLecteurNfc.uuidConnexion)
  }
}
// mémorise ancien état du lecteur nfc
const ancienEtatLecteurNfc = rfid.etatLecteurNfc
// remplace l'ancienne class par la class étendue simulant la lecture d'une carte
window.rfid = new emuleNfc()
// remet l'ancien état de la class rfid
rfid.etatLecteurNfc = ancienEtatLecteurNfc



// importe le module gérant les tests
import('/static/webview/electron_proj1/BaseTests.js').then(module2 => {
  // ajout de la méthode Test.init une fois le point de vente initial affiché
  window.Test = module2
  window.methods_after_render[1] = { method: Test.init }

  // Modifier si besoin les tagId utilisés lors des tests
  document.querySelector('#popup-cashless').innerHTML = `
    <div class="popup-titre1">Tests</div>
    <div class="BF-ligne-deb mh4px mb4px">
      <label class="popup-msg1">carte maîtresse</label>
      <input class="popup-msg1 mg8px" type="text" onchange="Test.modifierListeTagId(this,'carteMaitresse')" value="${ Test.listeTagId.carteMaitresse}">
    </div>
    <div class="BF-ligne-deb  mh4px mb4px">
      <label class="popup-msg1">carte client1</label>
      <input class="popup-msg1 mg8px" type="text" onchange="Test.modifierListeTagId(this,'carteClient1')" value="${ Test.listeTagId.carteClient1}">
    </div>
    <div class="BF-ligne-deb  mh4px mb4px">
      <label class="popup-msg1">carte client2</label>
      <input class="popup-msg1 mg8px" type="text" onchange="Test.modifierListeTagId(this,'carteClient2')" value="${ Test.listeTagId.carteClient2}">
    </div>
    <div class="BF-ligne popup-titre1 l50p fond-ok mh4px mb4px curseur-action" onclick="Test.lancer()">Lancer</div>
  `
}).catch((erreur) => {
  console.log('erreur: ', erreur)
})