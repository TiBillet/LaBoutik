const ipc = require('electron').ipcRenderer
let idElement = 0
//supprimer un élément du DOM
function supElement(element){
	//'id' ou 'class'
	let testTypeEle = element.substr(0,1);
	//id
	if(document.querySelector(element)!=null && testTypeEle=='#'){
		let sysElement = document.querySelector(element);
		sysElement.parentNode.removeChild(sysElement);
	}
	//class
	if(document.querySelectorAll(element)[0]!=null && testTypeEle=='.'){
		let sysElements = document.querySelectorAll(element);
		for (let i=0; i<sysElements.length; i++) {
			let sysElement = sysElements[i];
			sysElement.parentNode.removeChild(sysElement);
		}
	}
}

let typeElements = [
	{
		nom : 'titre',
		titre: { typeVar:'string', option: false },
		imgMenu: { typeFond: 'svg', valeur: 'letter-t' },
		information: 'Titre du test !'
	},{
		nom : 'elementClique',
		selecteur: { typeVar:'string', option: false },
		msg: { typeVar:'string', option: true },
		delay: { typeVar:'number', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'click' },
		information: 'Clique élément !'

	},{
		nom: 'elementExiste',
		selecteur: { typeVar:'string', option: false },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'zoom-check' },
		information: 'Elément existe ?'
	},{
		nom: 'elementExistePas',
		selecteur: { typeVar:'string', option: false },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'zoom-cancel' },
		information: 'Elément existe pas ?'
	},{
		nom: 'textElementEgal',
		selecteur: { typeVar:'string', option: false },
		valeur: { typeVar:'string', option: false },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'equal' },
		information: `Le text de l'élément est égal à ?`
	},{
		nom: 'numElementEgal',
		selecteur: { typeVar:'string', option: false },
		valeur: { typeVar:'number', option: false },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'number-7' },
		information: `La valeur(nombre) de l'élément est égal à ?`
	},{
		nom: 'elementVide',
		selecteur: { typeVar:'string', option: false },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'square' },
		information: `L'élément est vide ?`
	},{
		nom: 'elementPasVide',
		selecteur: { typeVar:'string', option: false },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'box-model-2' },
		information: `L'élément n'est pas vide ?`
	},{
		nom: 'elementTextInclut',
		selecteur: { typeVar:'string', option: false },
		valeur: { typeVar:'string', option: false },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'minus' },
		information: `L'élément contient le text ... ?`
	},{
		nom: 'elementInclutLesMots',
		selecteur: { typeVar:'string', option: false },
		mots: { typeVar:'string', option: false, info: `Séparer les mots d'une vigurle !` },
		msgOk: { typeVar:'string', option: true },
		msgEr: { typeVar:'string', option: true },
		imgMenu: { typeFond: 'svg', valeur: 'mist' },
		information: `L'élément contient les mots ... ?`
	}
]

function bougeDunElement(idElement,direction) {
	let cible = null, id
	if (direction === 'recule') {
		cible = document.querySelector(idElement).previousElementSibling
	} else {
		cible = document.querySelector(idElement).nextElementSibling
	}
	try {
		id = cible.id
	} catch (e) {
		id = null
	}
	if (id !== 'block-titre' && id!== null) {
		console.log('cible = ', cible)
		let clone = document.querySelector(idElement).cloneNode(true)
		supElement(idElement)
		if (direction === 'recule') {
			cible.insertAdjacentElement('beforebegin', clone)
		} else {
			cible.insertAdjacentElement('afterend', clone)
		}
	}
}

function activeDesactiveInput(ctx,id) {
	if (ctx.checked === true) {
		document.querySelector(id).disabled = false
	} else {
		document.querySelector(id).disabled = true
		document.querySelector(id).value = null
	}
}

function insertFormulaireElement(nomElement,valeurs) {
	let donnees = typeElements.filter(obj => obj.nom === nomElement)[0]
	idElement++
	// attributs
	let fragHtml = `
		<div id="block-${ nomElement }${ idElement }" class="BF-ligne-deb block-attributs l99p mg4px mh4px mb4px" data-nom-fonction="${ nomElement }">
			<div class="BF-col l5p">
				<img src="./../tabler-icons/${ donnees.imgMenu.valeur}.svg" style="width:24px;height:24px;">
			</div>
			<div class="BF-col-deb l89p block-liste-attributs" data-id="${ idElement }">
	`
	for (const clef in donnees) {
  	if (clef !== 'imgMenu' && clef !== 'information' && clef !== 'nom') {
  		let ignore = ``, bloque= ''
			if (donnees[clef].option === true) {
				ignore = `<input id="${ clef }-actif${ idElement }" type="checkbox" onChange="activeDesactiveInput(this,'#${ clef }-input${ idElement }')">`
				bloque = 'disabled'
			}
			let info = ''
			if (donnees[clef].info !== undefined) {
				info = `placeholder="${ donnees[clef].info }"`
			}
			let inputValeur = ''
			if (valeurs !== undefined) {
				if (valeurs[clef] !== undefined) {
					inputValeur = `value="${ valeurs[clef] }"`
				}
				if (valeurs[clef] !== null && valeurs[clef] !== undefined && donnees[clef].option === true) {
						ignore = `<input id="${ clef }-actif${ idElement }" type="checkbox" onChange="activeDesactiveInput(this,'#${ clef }-input${ idElement }')" checked>`
					bloque= ''
				}
			}
  		fragHtml += `
				<div class="BF-ligne-deb l100p mh2px mb2px block-entree">
					<div class="BF-ligne-d l10p">${ clef }</div>
					<input id="${ clef }-input${ idElement }" class="l80p" type="text" ${ info } ${ bloque } ${ inputValeur }>
					${ ignore }
				</div>
			`
		}
	}
	fragHtml += `
			</div>
			<div class="BF-col l5p h100p">
				<div class="BF-col h50p">
					<img class="h25p curseur-action" src="./../tabler-icons/trash.svg" style="width:24px;height:24px;" onClick="supElement('#block-${ nomElement }${ idElement }')">
				</div>
				<div class="BF-col h50p">
					<img class="h25p curseur-action" src="./../tabler-icons/caret-up.svg" style="width:24px;height:24px;" onclick="bougeDunElement('#block-${ nomElement }${ idElement }','recule')">
					<img class="h25p curseur-action" src="./../tabler-icons/caret-down.svg" style="width:24px;height:24px;" onclick="bougeDunElement('#block-${ nomElement }${ idElement }','avance')">
				</div>
			</div>
		</div>
	`
	document.querySelector('#tests').insertAdjacentHTML('beforeend', fragHtml)
	console.log('------------------------------------')
}

function composeMenuElementsTests() {
	let frag = ''
	for (let i = 0; i < typeElements.length; i++) {
		let menu = typeElements[i]
		let contenu = ''
		if (menu.imgMenu.typeFond === 'svg') {
			contenu = `<img src="./../tabler-icons/${ menu.imgMenu.valeur}.svg">`
		}
		frag += `
			<div class="BF-col curseur-action element" onclick="insertFormulaireElement('${ menu.nom }')" title="${ menu.information }">
				${ contenu }
			</div>
		`
	}

	document.querySelector('#outils').innerHTML = frag
}

function afficherinfo(info) {
	if (document.querySelector('#popup-adminTests') !== null) {
		console.log(`Suppression d'un ancien popup  !!!`)
		supElement('#popup-adminTests')
	}
	if (document.querySelector('#popup-adminTests') === null) {
		let frag = `
			<div id="popup-admin" class="BF-Col-BF-col">
				${ info }
				<div class="l100p BF-ligne popup-admin-retour-conteneur">
					<div id="popup-admin-retour" onclick="supElement('#popup-adminTests')">RETOUR</div>
				</div>
			</div>`
		document.querySelector('body').insertAdjacentHTML('beforeend',frag)
	}

}

function creerDonneesJson() {
	let objTest = []
	let blockAttributs = document.querySelectorAll('#tests .block-attributs')
	for (let bt = 0; bt < blockAttributs.length; bt++) {
		obj = {}
		obj.fonction = blockAttributs[bt].getAttribute('data-nom-fonction')
		let blockData = blockAttributs[bt].querySelector('.block-liste-attributs')
		let idBlockData = blockData.getAttribute('data-id')
		let entrees = blockData.querySelectorAll('.block-entree')
		obj.entrees = {}
		for (let e = 0; e < entrees.length; e++) {
			let entree = entrees[e]
			let nomEntree = entree.querySelector('div').innerHTML
			// console.log('nomEntree = ', nomEntree)
			let valeurElement = entree.querySelector(`#${ nomEntree }-input${ idBlockData }`).value
			// console.log('valeurElement = ', valeurElement)
			let desactive = entree.querySelector(`#${ nomEntree }-input${ idBlockData }`).disabled
			if (desactive === false) {
				obj.entrees[nomEntree] = valeurElement

			}
			// console.log('------------------------')
		}
		objTest.push(obj)
	}
	console.log('objTest = ', objTest)
	return objTest
}

ipc.on('afficherFichierTest', (event, data) => {
	composeMenuElementsTests()
	let dataJson = JSON.parse(data)
	document.querySelector('#tests').innerHTML = ''
	for (let i = 0; i < dataJson.length; i++) {
		let element = dataJson[i]
		insertFormulaireElement(element.fonction, element.entrees)
	}

})

// demande les données à sauvegarder
ipc.on('demandeDonneesPourSauvegarde', (event, nomFichier) => {
		if (document.querySelectorAll('.block-attributs').length > 1) {
			let data = creerDonneesJson()
			ipc.send('donneesJsonPourSauvegarde', { data: data, nomFichier: nomFichier })
		} else {
			afficherinfo('<div class="BF-ligne l100p mh8px mb8px">Aucune action entrée !</div>')
		}
})

ipc.on('test', (event, message) => {
	// insertion d'icones pour composer un test
	if (message === "nouveau") {
		composeMenuElementsTests()
		document.querySelector('#tests').innerHTML = ''
		insertFormulaireElement('titre')
	}
	if (message === 'demandeLancerTests') {
		if (document.querySelectorAll('.block-attributs').length > 1) {
			let retour = creerDonneesJson()
			ipc.send('donneesJsonPourLancerTests', retour)
		} else {
			afficherinfo('<div class="BF-ligne l100p mh8px mb8px">Aucune action entrée !</div>')
		}
	}
})

ipc.on('popup', (event, message) => {
	afficherinfo(message)
})