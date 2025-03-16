// bouton basique, attribut "texte":
// exemple : texte="CASHLESS|2rem|,[TOTAL] ${total} [€]|1.5rem||total-uppercase;currencySymbol"

import { getTranslate } from "../modules/i8n.js"

// information: texte="mot [mot à trduire] mot [mot à trduire] mot| taille fonte | couleur fonte | index de traduction - option ; index de traduction - option"
function btTranslate(texte, translateDirectivesRaw) {
  const translateDirectives = translateDirectivesRaw.split(';')
  let index = 0, words = [], trad = '', record = 'none', mot = '', tradOn = false, directives = []

  for (let id = 0; id < translateDirectives.length; id++) {
    const directiveRaw = translateDirectives[id].split('-')
    directives.push({ word: directiveRaw[0], option: directiveRaw[1], index: id })
  }

  if (texte.includes("[") === true && texte.includes("]") === true) {
    // plusieurs traductions dans la ligne !
    for (let i = 0; i < texte.length; i++) {
      const l = texte[i]
      if (record === 'stop') {
        record = 'none'
        tradOn = false
      }
      if (record === 'start') {
        record = 'on'
        tradOn = true
      }
      if (l === "[") {
        record = 'start'
        if (mot.length > 0) {
          words.push({ word: mot, trad: tradOn })
        }
        mot = ''
      }
      if (l === "]") {
        record = 'stop'
        index++
        if (mot.length > 0) {
          words.push({ word: mot, trad: tradOn, index: index - 1 })
        }
        mot = ''
      }
      if (record === 'on' || record === 'none') {
        mot += l
      }
    }

    if (directives.length === index) {
      for (let im = 0; im < words.length; im++) {
        const word = words[im]
        if (word.trad === true) {
          const directive = directives.find(item => item.index === word.index)
          word.word = getTranslate(directive.word, directive.option)
        }
        trad += word.word
      }
    } else {
      // Attention: pas de traduction, erreur dans les données de traduction; voir [] ou index de traduction
      console.log(getTranslate("impossibleTranslation"))
      for (let im = 0; im < words.length; im++) {
        const word = words[im]
        trad += word.word
      }
 
    }
    return trad
  } else {
    // une traduction dans la ligne
    const translateDirective = translateDirectives[0].split('-')
    return getTranslate(translateDirective[0], translateDirective[1])
  }
}

function get_template(ctx) {
  // console.log('largeur = '+ctx.largeur);

  return `
    <style>
      .BF-ligne-uniforme {
        display: flex;
        flex-direction: row;
        justify-content: space-evenly;
        align-items: center;
      }
      :host{
        box-sizing: border-box;
        width: ${parseFloat(ctx.largeur.substring(0, ctx.largeur.length - 2)) * (7 / 10) + 'px'};
        height:  ${parseFloat(ctx.hauteur.substring(0, ctx.hauteur.length - 2)) * (3 / 4) + 'px'};
        background: ${ctx.couleur_fond} ;
        cursor: pointer;
        overflow: hidden;
      }
      .sous-element{
        width: 100%;
        height: 100%;
      }
      .sous-element:hover{
        background: #15181e;
      }
      .sous-element-texte{
        /*display: block;*/
        color: #FFFFFF;
        font-weight: bold;
        font-size: 26px;
        line-height: 26px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
      }

      /* largeur maxi 600 pixels */
      @media only screen and (min-width: 599px){
      :host{
        width: ${ctx.largeur};
        height:  ${ctx.hauteur};
      }

      /* pour une largeur de 1024px */
      @media only screen and (min-width: 1023px) {
        :host {
          width: ${ctx.largeur};
          height: ${parseFloat(ctx.hauteur.substring(0, ctx.hauteur.length - 2)) * (3 / 4) + 'px'};  
        }
      }
    </style>
    <link rel="stylesheet" href="/static/webview/css/all_fontawesome-free-5-11-2.css">
    <div class="sous-element BF-ligne-uniforme">
      ${ctx.icon}
      <div class="sous-element-texte">
        ${ctx.texte}
      </div>
    </div>
  `
}

export default class BoutonBasique extends HTMLElement {
  connectedCallback() {
    this.couleur_fond = this.getAttribute('couleur-fond')
    let texte = this.getAttribute('texte')
    // console.log('-> BoutonBasique, texte =', texte);
    
    const i8n = this.getAttribute('i8n')
    this.largeur = this.getAttribute('width');
    this.hauteur = this.getAttribute('height');
    let largeur_ecran = document.querySelector('body').clientWidth

    // affichage de l'icon d'un bouton
    this.icon = '';
    if (this.getAttribute('icon') !== null) {
      let icon_size = '3rem', icon_color = '#FFFFFF';
      let data_icon = this.getAttribute('icon').split('|'); // icon|couleur|taille avec unité
      let icon_img = data_icon[0];
      if (data_icon[1] !== undefined) icon_color = data_icon[1];
      if (data_icon[2] !== undefined) icon_size = data_icon[2];
      // console.log('couleur = '+data_icon[1]+'  --  size = '+data_icon[2]);
      this.icon = `
        <div style="color:${icon_color};font-size:${icon_size};">
          <i class="fas ${icon_img}"></i>
        </div>
      `;
    }

    // affichage du texte d'un bouton
    this.texte = '';
    let traiter = this.getAttribute('traiter-texte');
    if (traiter === '1') {
      let donnees_mixees = texte.split(',');
      for (let i = 0; i < donnees_mixees.length; i++) {
        let donnees = donnees_mixees[i].split('|');

        // texte
        let texte_contenu = '';
        if (donnees.length > 0) texte_contenu = donnees[0];

        // style appliqué pour chaque ligne si données existe 'texte|font size| font color'
        let texte_style = '', font_style = '', color_style = '';
        // taille fonte obligatoirement en rem
        if (donnees.length > 1 && donnees[1] !== '') {
          // console.log('taille retour = ' + donnees[1]) parseFloat(ctx.hauteur.substring(0,ctx.hauteur.length-2))*(3/4)+'px'
          let font_size = parseFloat(donnees[1].substring(0, donnees[1].length - 3))
          // simu media query  ecran 1020-1024
          if (largeur_ecran >= 1020 && largeur_ecran <= 1024) {
            font_size = parseFloat(donnees[1].substring(0, donnees[1].length - 3)) * (3 / 4)
          }
          font_style += 'font-size:' + font_size + 'rem;'
        }
        // couleur
        if (donnees.length > 2 && donnees[2] !== '') color_style += 'color:' + donnees[2] + ';';
        if (font_style !== '' || color_style !== '') texte_style += 'style="' + font_style + color_style + '"';

        // translate ask
        if (donnees.length === 4) {
          texte_contenu = btTranslate(texte_contenu, donnees[3])
        }

        // composition du contenu(intérieur) du bouton
        this.texte += `
          <div ${texte_style}>
            ${texte_contenu}
          </div>
        `;
      }
    } else {
      this.texte = `<div class="BF-ligne l100p" ${i8nAttribute}>${texte}</div>`
    }

    this.attachShadow({ mode: 'open' }).innerHTML = get_template(this);
  }
}
