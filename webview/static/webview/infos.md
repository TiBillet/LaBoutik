# traduction:

## Langues
Les langues sont définies dans  ".../webview/static/webview/js/modules/i8n.js"
```
lang = {
  langue choisie/chosen language: {
    index de traduction/single translation index: "traduction/translation",
    index de traduction/single translation index: "traduction/translation",
  }
}
# exemple:
const lang = {
  "fr-FR": {
    waitPrimaryCard: "attente carte primaire",
    confirmPayment: "confirmez le paiement"
  },
 "en-GB": {
    waitPrimaryCard: "waiting\nprimary card",
    confirmPayment: "confirm the payment"
 }
}
```
## Choix de la langue à traduire 
La langue utilisée est configurée dans le template django "modele00.html"
```
<script>
      // "fr-FR" , "en-GB"
      window.local = "en-GB" // "fr-FR"
</script>
```
## Utilisations
### . Insertion d'un fragment html dans le DOM
Repérer une insertion html par le code ".innerHTML =" et .insertAdjacentHTML('....',fragmentHtml).   
L'attribut "data-i8n" permet de repérer l'élément à traduire et remplacer le text,   
ça valeur contient l'index de traduction seul ou avec une option(séparés par une virgule).   

#### Options de traduction :
. capitalize = Première lettre en majuscule.   
. uppercase = Tous en majuscule.

#### Exemple :
```
# fragment html
const fragmentHtml = `<div>
  <h1>
    <div class="BF-ligne" data-i8n="confirmPayment, capitalize">Confirmez le paiement</div>
  </h1>
</div>`

// insertion fragment html
document.querySelector('#contenu').insertAdjacentHTML('beforeend',fragmentHtml)

// la recherche de mots à traduire se fait sur l'élément où le fragment html
// a été inséré : "#contenu" 
translate('#contenu')`
```
#### Attention, l'insertion d'un fragment html dans le DOM doi être suivi de la commande "translate"
Le code translate permet de lancer le processus de traduction l'hors de l'insertion dynamique dans le dom.

### . Messages popup et rfid(utilise popup)
Vous utilisez uniquement l'attribut 'data-i8n="indexTrduction,option"'   
Pas besoin du code "translate('#cible')".

### . Bouton-basique
- Pas besoin du code "translate('#cible')".   
- Il peut y avoir plusieurs mots sur différentes lignes.
- Vous utilisez uniquement l'attribut 'texte' :   
" partie text | partie taille fonte | partie couleur fonte | partie traduction "
- "|" sépare les données à traiter (text, taille, couleur et traduction )
- "," sépare une ligne à traiter et à afficher.
- "[...]" dans la partie text, permet de traiter plusieurs traductions d'une ligne.
- Plusieurs traductions sur une ligne, la partie traduction est définie ainsi :   
indexTraductionMot1-option;indexTraductionMot2-option;... 

#### exemple :
```
<bouton-basique ... texte="RETOUR|2rem||return-uppercase" ...></bouton-basique>   
<bouton-basique ... texte="CB|2rem|,[TOTAL] ${totalManque} [€]|1.5rem||cb-uppercase;currencySymbol" ...></bouton-basique>
```

# Ajouter un item au menu
Dans ".../webview/static/webview/js/menuPlugins/addAllMenuPlugin.js":   
Ajouter le nom de dossier de votre nouvel item dans la variable listMenuToAdd = ["pettyCash", "itemn", "mon_nouveau_dossier"],   
l'index du tableau donne l'ordre d'affichage. 

## Définir votre item de menu  et coder vos fonctions liées
- Le contenu du menu doit déclaré comme suit:
. func = fonction appelé suite au clique menu.   
. icon = icon du menu (font awesome 5.11, contenu tag i)   
. i8nIndex = index de traduction pour les langues définies dans "i8n.js"   

```
export const menu = {
    func: "pettyCashInterface",
    icon: "fas fa-money",
    i8nIndex: "pettyCash,uppercase"
}
```

- Les fonctions accédées par un click, exemple "onclick=functionTest()"   
doivent être déclarées de façon globale.
```
window.functionTest = function () {
    .......
}
```
### exemple
```
window.pettyCashAction = function () {
  console.log("-> pettyCashAction !")
}

window.pettyCashInterface = function () {
    // console.log('-> fond de caisse / pettyCash')
    // efface le menu
    document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
    // popup de confirmation
    let message = `
   <div id="popup-cashless-confirm" class="BF-col popup-cashless-confirm-conteneur">
    <div class="BF-col" style="margin: 0 2%;">
     <h1>Petty Cash Interface</h1>
    </div>
    <div class="BF-ligne-entre">
      <bouton-basique id="popup-confirme-retour" traiter-texte="1" texte="RETOUR|1.5rem||return-uppercase" couleur-fond="#3b567f" icon="fa-undo-alt||2rem" width="240px" height="100px"  onclick="fn.popupAnnuler();" style="margin: 8px"></bouton-basique>
      <bouton-basique id="popup-confirme-valider" traiter-texte="1" texte="VALIDER|1.5rem||validate-uppercase" couleur-fond="#339448" icon="fa-check-circle||2rem" width="240px" height="100px"  onclick="fn.popupAnnuler();pettyCashAction();" style="margin: 8px;"></bouton-basique>
    </div>
   </div>
  `
    let options = {
        message: message,
        type: 'normal'
    }
    fn.popup(options)
}

export const menu = {
    func: "pettyCashInterface",
    icon: "fa-money", // font awesome 4
    i8nIndex: "pettyCash,uppercase"
}

```
