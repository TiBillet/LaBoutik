function getTemplate(ctx) {
  // sys.logJson('ctx = ', ctx)

  let template = `
    <style>
      @font-face {
        font-family: 'Source Sans';
        src: url('../../css/googlefonts/SourceSansPro-Regular.ttf') format("truetype");
      }
      :host {
        box-sizing: border-box;
        width: 120px;
        height: 120px;
        cursor: pointer;
        overflow: hidden;
        border-radius: 15px;
        background-color: ${ctx.couleurFond};
        margin: 20px 0 0 20px;
        float: left;
      }

      .ele-conteneur {
        position: relative;
        font-family: 'Source Sans', sans-serif;
        box-sizing: border-box;
        width: 100%;
        height: 100%;
        border-radius: 15px;
      }

      .ele-nom {
        position: absolute;
        left: 8px;
        top: 6px;
        font-weight: bold;
        max-height: 60px;
        font-size: 20px;
        margin-top: 0;
        margin-bottom: 1rem;
        color: ${ctx.couleurTexte};
        overflow: hidden;
      }

      .ele-img {
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
      }

      .BF-ligne {
        align-items: center;
        display: flex;
        flex-direction: row;
        justify-content: center;
      }

      .BF-ligne-g{
        align-items: center;
        display: flex;
        flex-direction: row;
        justify-content: flex-start;
        width: 100%;
      }

      .article-pdp {
        position: absolute;
        left: 8px;
        bottom: 8px;
      }

      .article-statut {
         position: absolute;
         width: 21px;
         height: 21px;
         right: 4px;
         bottom: 34px;
         color: #FFFFFF;
         font-size: 16px;
         font-weight: bold;
         border-radius: 50%;
      }

      .article-statut-icon {
        font-size: 24px;
      }
      
      .ele-icon {
        flex-basis: 25%;
        color: ${ctx.couleurTexte};
      }

      .ele-prix {
        flex-basis: 45%;
        color: ${ctx.couleurTexte};
      }

      .ele-nombre {
        flex-basis: 25%;
      }

      .badge {
        color: #212529;
        background-color: #f8f9fa;
        display: inline-block;
        padding: .25em .4em;
        font-weight: bold;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: .25rem;
        transition: color .15s ease-in-out,background-color .15s ease-in-out,border-color .15s ease-in-out,box-shadow .15s ease-in-out;
      }

      #bt-rideau{
        position: absolute;
        left: 0px;
        top: 0px;
        width: 100%;
        height: 100%;
        border-radius: 15px;
        background-color: #2a2828;
        opacity: 0.5;
        cursor: default;
        display: none;
      }

      /* largeur maxi 600 pixels */
      @media only screen and (min-width: 599px){
        :host {
          width: 140px;
        }
      }

      /* largeur maxi 1024 pixels */
      @media only screen and (min-width: 1023px) {
        :host {
          width: 100px;
          height: 100px;
        }
        .ele.img {
          width: 100px;
          height: 100px;
        }
        .ele-nom {
          font-size: 16px;
        }
        .ele-prix {
          flex-basis: 40%;
        }
      }

      /* largeur maxi 1200 pixels */
      @media only screen and (min-width: 1199px) {
        :host {
          width: 240px;
          height: 240px;
          margin: 8px;
        }
        .ele-img img {
          transform: scale(2);
        }
        .ele-nom {
          font-size: 32px;
          max-height: 120px;
          width: 96%;
        }
        .article-statut {
          width: 21px;
          height: 21px;
          right: 26px;
          bottom: 68px;
          font-size: 32px;
        }
        .article-statut-icon {
          font-size: 48px;
        }
        .article-pdp {
          width: 93%;
          font-size: 32px;
        }
        .ele-prix {
          flex-basis: 51%;
        }
        
      }

    </style>
    <link rel="stylesheet" href="/static/webview/css/all_fontawesome-free-5-11-2.css">
    <div class="ele-conteneur">
      ${ctx.afficherImage()}
      <div class="ele-nom">
        ${ctx.nom}
      </div>
      ${ctx.afficherStatut()}
      <div class="article-pdp BF-ligne-g">
        <div class="ele-icon">${ctx.infoIcon}</div>
        ${ctx.afficherPrix()}
        <div class="ele-nombre BF-ligne">
          <span id="rep-nb-article${ctx.articleUuid}" class="badge">${ctx.nbCommande
    }</span>
        </div>
      </div>
      <div id="bt-rideau"></div>
      ${ctx.vaseCommunicant()}
    </div>
  `
  return template
}

export default class BoutonCommandeArticle extends HTMLElement {
  static get observedAttributes() {
    return ["nb-commande"]
  }

  connectedCallback() {
    let data = this.getAttribute("data")
    let article = JSON.parse(unescape(data))
    // sys.logJson('article -> ',article);
    // console.log('-----------------------------------------------')

    this.articleUuid = article.uuid
    this.prix = article.prix
    this.nom = article.name
    this.img = article.urlImage
    this.nbCommande = article.nbMax
    this.methode = article.methodeName
    this.nomModule = article.nomModule
    this.commandes = article.commandes
    this.uuidArticlePaiementFractionne = article.uuidArticlePaiementFractionne
    this.resteAservir = article.resteAservir
    this.statut = article.statut

    // couleur de fond de la categorie
    // par défaut
    this.couleurFond = "#189ac8"
    // icon
    this.infoIcon = ""
    if (article.categorie !== undefined && article.categorie !== null) {
      // affiche ou pas le fond
      if (article.categorie.couleur_backgr !== null) {
        this.couleurFond = article.categorie.couleur_backgr
      }
      // couleur du texte par défaut
      this.infoIcon = '  <i class="fas ' + article.categorie.icon + '"></i>'
      this.couleurTexte = article.categorie.couleurTexte
    }

    // couleur du texte de l'article prioritaire pour mieux resortir sur l'image
    if (article.couleurTexte !== null) this.couleurTexte = article.couleurTexte
    if (this.couleurTexte === undefined || this.couleurTexte === null)
      this.couleurTexte = "#FFFFFF"

    this.setAttribute("nb-commande", this.nbCommande)
    this.setAttribute("ajout-article", "")

    this.attachShadow({ mode: "open" }).innerHTML = getTemplate(this)

    this.addEventListener("click", this.decrement, false)
    this.classList.add("bouton-commande-article")

    this.removeAttribute("data")
  }

  vaseCommunicant() {
    let fragVase = `<div id="vase-communicant-article${this.articleUuid}">`
    for (let i = 0; i < this.commandes.length; i++) {
      let commande = this.commandes[i]
      // console.log('commande = ', commande)
      for (let j = 0; j < commande.qty; j++) {
        fragVase += `
          <div class="article-commande" data-methode="${this.methode}" data-uuid-article="${this.articleUuid}" data-uuid-commande="${commande.uuidCommande}" 
          data-responsable="${commande.responsable}" data-date-commande="${commande.dateCommande}"
          data-prix="${this.prix}" data-nom="${this.nom}"></div>
        `
      }
    }

    fragVase += "</div>"
    return fragVase
  }

  /*
  "PP", "PR", "SV", "PY", "SP"
   */
  afficherStatut() {
    let couleurs = {
      PP: "#FF0000",
      PR: "#c65a07",
      SV: "#339448",
      PY: "#0048ff",
      SP: "#bfc9c9",
    }
    return `
      <!-- <div class="article-statut BF-ligne" style="background-color: ${couleurs[this.statut]
      }"> -->
      <div class="article-statut BF-ligne"> 
        <i class="article-statut-icon fas fa-concierge-bell" style="color: ${couleurs[this.statut]
      }"></i>
      </div>
      <div class="article-statut BF-ligne">
        ${this.resteAservir}
      </div>
    `
  }

  afficherPrix() {
    return `
       <div class="ele-prix BF-ligne-g">
          ${this.prix} ${getTranslate('currencySymbol', null, 'methodCurrency')}
       </div>
    `
  }

  /**
   * Affiche une image dans le bouton article
   * @returns {string} template div contenant une image
   */
  afficherImage() {
    if (typeof this.img === "string") {
      return `
          <div class="ele-img BF-ligne">
            <img src="${this.img}" loading="lazy" onerror="this.style.display='none'">
          </div>
     `
    }
    return ""
  }

  decrement() {
    // vérifier que l'ajout de cet article dans l'addition en cours ne dépasse pas la somme à payer
    let resteAPayer = parseFloat(document.querySelector("#commandes-table-contenu").getAttribute("data-reste-a-payer"))
    let additionEncours = parseFloat(document.querySelector("#commandes-table-contenu").getAttribute("data-total-addition-en-cours"))

    // console.log('-> fonc decrement de bouton_commande_article.js')
    // console.log('resteAPayer = ', resteAPayer)
    // console.log('additionEncours = ', additionEncours)

    let depassementResteAPayer = 0
    if (this.prix + additionEncours > resteAPayer) {
      depassementResteAPayer = 1
      // fait un paiement fractionné avec ce qui reste à payer

      let cible = document.querySelector("#commandes-table-contenu")
      let idTable = cible.getAttribute("data-idTable")
      let nomTable = cible.getAttribute("data-nomTable")

      let actionAValider = "addition_fractionnee"
      let options = {
        url: "paiement",
        actionAValider: actionAValider,
        messageResteAPayer: 0,
        valeurEntree: resteAPayer,
        idTable: idTable,
        nomTable: nomTable,
      }
      // les articles sélectionnés
      let achats = vue_pv.obtenirAchats(actionAValider, options)
      options.achats = achats
      vue_pv.validerEtape1(options)
    }
    // console.log('depassementResteAPayer = ', depassementResteAPayer)

    // vérifie que le nombre d'article est supérieur à 0 (non null)
    let premierEnfant = this.shadowRoot.querySelector(
      `.ele-conteneur #vase-communicant-article${this.articleUuid}`
    ).firstElementChild
    if (premierEnfant !== null && depassementResteAPayer === 0) {
      // clone le premier élément
      let clone = premierEnfant.cloneNode(true)

      // copier dans le vase communicant de l'addition
      document.querySelector("#addition-vase-communicant").append(clone)

      // Supprime le premier enfant
      premierEnfant.parentNode.removeChild(premierEnfant)

      // décrément le nbCommande
      this.nbCommande--
      this.setAttribute("nb-commande", this.nbCommande)
    }
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === "nb-commande") {
      this.nbCommande = this.getAttribute("nb-commande")
      if (this.shadowRoot !== null) {
        // maj nombre article
        this.shadowRoot.querySelector(`#rep-nb-article${this.articleUuid}`).innerHTML = this.nbCommande
        // maj liste addition
        restau.majListeAddition()
      }

      // cache l'élément
      if (this.nbCommande === "0") {
        this.style.display = "none"
      } else {
        this.style.display = "block"
      }
    }
  }
}
