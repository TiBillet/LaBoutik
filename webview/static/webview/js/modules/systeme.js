// --- pour déterminer la résolution en X ---
var Xresolution = 0;

export function bigToFloat(value) {
	try {
		return parseFloat(new Big(value).valueOf())
	} catch (error) {
		console.log('-> bigToFloat de sys, ', error)
	}
}

/**
 * Passer un object javascript à un attribut html
 *@param {object} obj = objet à transmettre au html
 *@return {string}
 */
export function html_pass_obj_in(obj) {
	// TODO: vérifier que c'est un objet, si non log un message
	return escape(JSON.stringify(obj));
}

/**
 * Créer un uuid
 * @returns {string}
 */
export function uuidV4() {
	return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
		let r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8)
		return v.toString(16)
	})
}

/**
 * Trier un tableau d'objet par ordre croissant en fonction de l'attribut donné
 * @param {Object} objet
 * @param {String} attribut
 * @return {Array} tabObj
 */
export function trierTableauObjetCroissantFoncAttribut(objet, attribut) {
	return objet.sort((a, b) => {
		if (a[attribut] < b[attribut]) return -1
		if (a[attribut] > b[attribut]) return 1
		return 0
	})
}

/**
 * Trier un tableau d'objet par ordre décroissant en fonction de l'attribut donné
 * @param {Object} objet
 * @param {String} attribut
 * @return {Array} tabObj
 */
export function trierTableauObjetDecroissantFoncAttribut(objet, attribut) {
	return objet.sort((a, b) => {
		if (a[attribut] < b[attribut]) return 1
		if (a[attribut] > b[attribut]) return -1
		return 0
	})
}

/**
 * Trier un tableau d'objet par ordre alphanumérique
 * @param {Object} objet
 * @param {String} attribut
 * @return {Array} tabObj
 */
export function trierTableauObjetAlphaNumerique(objet, attribut) {
	return objet.sort((a, b) => {
		let aVal = a[attribut].toLowerCase()
		let bVal = b[attribut].toLowerCase()

		if (aVal < bVal) {
			return -1
		}
		if (aVal > bVal) {
			return 1
		}
		return 0
	})
}


/**
 * Tester l'existance d'un fichier
 *
 * @export
 * @param {string} src url du fichier à tester
 * @returns {boolean}
 */
export function testFichierExiste(src) {
	const http = new XMLHttpRequest()
	http.open('HEAD', src, false)
	http.send()
	if (http.status === 200) {
		return true
	}
	return false
}

/**
 * Afficher la valeur des variable
 * @param {Array} - liste
 */
export function logValeurs(liste) {
	// obtenir le nom de la fonction appelante et son numéro de ligne
	let mots, fonc, num, col
	let testChrome = window.navigator.userAgent.indexOf('Chrome')
	let testFirefox = window.navigator.userAgent.indexOf('Firefox')
	if (testFirefox !== -1) {
		let lignes = (new Error()).stack.split('\n')[1]
		fonc = (lignes.split('@')[0]).replace('/', '').replace('<', '')
		let numTab = (lignes.split('@')[1]).split(':')
		let col = numTab[numTab.length - 1]
		num = numTab[numTab.length - 2]
		let foncMereTab = (numTab[numTab.length - 3]).split('/')
		let foncMere = foncMereTab[foncMereTab.length - 1]
		console.log('--> sys.logJson appelée par la fonction "' + fonc + '" à la ligne numéro ' + num + ' et à la colonne ' + col + ' -- provenant de "' + foncMere + '"')
	}
	if (testChrome !== -1 || window.navigator.userAgent.indexOf('modeNfc')) {
		mots = ((new Error()).stack.split('\n')[2]).split('/')
		let tempoData = (mots[mots.length - 1]).split(':')
		fonc = tempoData[tempoData.length - 3]
		num = tempoData[tempoData.length - 2]
		col = tempoData[tempoData.length - 1]
		console.log('--> sys.logValeurs appelée par la fonction "' + fonc + '" à la ligne numéro ' + num + ' et à la colonne ' + col)
	}

	for (const clef in liste) {
		if (typeof liste[clef] !== 'object') {
			console.log(typeof liste[clef], ' -> ', clef, ' = ', liste[clef])
		} else {
			console.log(typeof liste[clef], ' -> ', clef, ' = ', JSON.stringify(liste[clef], null, '\t'))
		}
	}
	console.log('--------------------------------------------------------------')
}

/**
 * Affiche des information en local, distant ou les deux
 * @param {String} infos
 */
export function log(infos) {
	// window.DEBUG  = local, distant, deux
	if (window.DEBUG === 'local') {
		console.log(infos)
	}
	if (window.DEBUG === 'distant') {
		if (SOCKET_DEBUG) {
			SOCKET_DEBUG.emit('log', infos)
		} else {
			console.log('Débug distant impossible, pas de SOCKET_DEBUG !')
		}
	}
}

/**
 * Log objets ou varaiables en les convertissant en chaine de caractères
 * @export
 * @param {string} infos = informations diverses
 * @param {Object} obj = objet ou variable à convertir en chaine dee caractère
 */
export function logJson(infos, obj) {
	let mots, fonc, num, col
	let testChrome = window.navigator.userAgent.indexOf('Chrome')
	let testFirefox = window.navigator.userAgent.indexOf('Firefox')
	if (testFirefox !== -1) {
		let lignes = (new Error()).stack.split('\n')[1]
		fonc = (lignes.split('@')[0]).replace('/', '').replace('<', '')
		let numTab = (lignes.split('@')[1]).split(':')
		let col = numTab[numTab.length - 1]
		num = numTab[numTab.length - 2]
		let foncMereTab = (numTab[numTab.length - 3]).split('/')
		let foncMere = foncMereTab[foncMereTab.length - 1]
		console.log('--> sys.logJson appelée par la fonction "' + fonc + '" à la ligne numéro ' + num + ' et à la colonne ' + col + ' -- provenant de "' + foncMere + '"')
	}
	if (testChrome !== -1 || window.navigator.userAgent.indexOf('modeNfc')) {
		mots = ((new Error()).stack.split('\n')[2]).split('/')
		let tempoData = (mots[mots.length - 1]).split(':')
		fonc = tempoData[tempoData.length - 3]
		num = tempoData[tempoData.length - 2]
		col = tempoData[tempoData.length - 1]
		console.log('--> sys.logJson appelée par la fonction "' + fonc + '" à la ligne numéro ' + num + ' et à la colonne ' + col)
	}
	console.log(infos + JSON.stringify(obj, null, '\t'))

}

// positionne un élément au centre de l'écran
export function centrerPosition(largeurElement, hauteurElement) {
	let ex = window.innerWidth;
	let ey = window.innerHeight;
	let px = Math.round((ex / 2) - (largeurElement / 2));
	let py = Math.round((ey / 2) - (hauteurElement / 2));
	return { x: px, y: py };
}

//génère un nombre aléatoire
export function rnd(maxi) {
	let min = Math.ceil(0);
	let max = Math.floor(maxi);
	return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function dom_insert_avant(id, element) {
	let cible = document.querySelector('#' + id);
	let parent = cible.parentNode;
	parent.insertBefore(element, cible);
}

export function dom_insert_apres(id, element) {
	let cible = document.querySelector('#' + id);
	cible.parentNode.insertBefore(element, cible.nextSibling);
}

// insère un élément DOM dans un autre élément avant le premier enfant
// id = où insérer, element = élément à insérer
export function dom_insert_premier(id, element) {
	let rep_ele = document.querySelector('#' + id);
	rep_ele.insertBefore(element, rep_ele.firstChild);
}

// insère un élément DOM dans un autre élément après le dernier des enfants
// id = où insérer, element = élément à insérer
export function dom_insert_dernier(id, element) {
	let rep_ele = document.querySelector('#' + id);
	rep_ele.append(element);
}

//supprimer un élément du DOM
export function supElement(element) {
	//'id' ou 'class'
	let testTypeEle = element.substr(0, 1);
	//id
	if (document.querySelector(element) != null && testTypeEle == '#') {
		let sysElement = document.querySelector(element);
		sysElement.parentNode.removeChild(sysElement);
	}
	//class
	if (document.querySelectorAll(element)[0] != null && testTypeEle == '.') {
		let sysElements = document.querySelectorAll(element);
		for (let i = 0; i < sysElements.length; i++) {
			let sysElement = sysElements[i];
			sysElement.parentNode.removeChild(sysElement);
		}
	}
}

// divise une chaine en fonction d'un espace situé avant ou après un nombre donné de caractères
export function diviseEspaceNbCarac(chaine, nbc) {
	let retour = [], maxC = 0, derEspace = 0, boucle = 1, s = '', cp = '';
	while (boucle == 1) {
		s = chaine.substring(0, nbc);
		derEspace = s.lastIndexOf(' ');
		cp = chaine.substring(0, derEspace);
		if (cp.length > maxC) maxC = cp.length;
		retour.push(cp);
		chaine = chaine.substring(derEspace + 1, chaine.length);
		if (chaine.length < nbc) {
			boucle = 0;
			retour.push(chaine);
		}
	}
	// console.log('-> retour = '+retour);
	return { "text": retour, "maxC": maxC };
}

/** @function
 * Visuel du temps de chargement
 * @param {Object.<etat, largeur, rpt, nbc, epaisseur, couleur, typeVisuChargement>} options - variables du visuel de téléchargement
 */
export function affCharge(options) {
	// console.log('-> fonction sys.affCharge !')
	// sys.logJson('options = ', options)

	// par défaut, affichage de l'icon(svg) de chargement
	if (options.typeVisuChargement === undefined) {
		options.typeVisuChargement = 'defaut'
	}

	// visuel chargement par défaut
	if (options.typeVisuChargement === 'defaut') {
		// afficher le loader
		if (options.etat === 1 && document.querySelector('#fond_aff_charge') === null) {
			const ex = window.innerWidth;
			const ey = window.innerHeight;
			let fragCharge = `<div id="fond_aff_charge"><div id="conteneur_aff_charge"><div id="cercle_aff_charge">
				<svg width="${options.largeur}" height="${options.largeur}" viewBox="0 0 ${options.largeur} ${options.largeur}">`;
			const r = (options.largeur / 2) - options.rpt;
			for (let i = 0; i < options.nbc; i++) {
				const ang = i * (Math.PI * 2) / options.nbc;
				const px = (options.largeur / 2) + Math.cos(ang) * r;
				const py = (options.largeur / 2) + Math.sin(ang) * r;
				fragCharge += `<circle class="petit_cercle_aff_charge" cx="${px}" cy="${py}" r="${options.rpt}" fill="currentColor"/>`;
			}
			const perimetre = 2 * Math.PI * (options.largeur - options.epaisseur)
			fragCharge += `</svg>
				<svg id="trainee_aff_charge" width="${options.largeur}" height="${options.largeur}" viewBox="0 0 ${options.largeur} ${options.largeur}" fill="none">
					<circle cx="${(options.largeur / 2)}" cy="${(options.largeur / 2)}" r="${(options.largeur / 2) - 2}" stroke="currentColor" stroke-width="${options.epaisseur}"/>
				</svg>
			</div>
			<style>
				#fond_aff_charge {
					position: absolute;
					left: 0;
					top: 0;
					width: 100%;
					height: 100%;
					/*background-color: #000;*/
					opacity: 0.5;
				}
				#conteneur_aff_charge{
					position: fixed;
					left: ${((ex / 2) - (options.largeur / 2))}px;
					top:  ${((ey / 2) - (options.largeur / 2))}px;
					color: ${options.couleur};
					width: 100%;
					height: 100%;
				}
				#cercle_aff_charge{
					position: relative;
					width: ${options.largeur}px;
					height: ${options.largeur}px
				}
				.petit_cercle_aff_charge{
					transform-origin: center;
					animation: tournePetitCercle 16s linear infinite;
				}
				#trainee_aff_charge{
					position: absolute;
					left: 0;
					top: 0;
					stroke-dasharray: ${perimetre};
					stroke-dashoffset: ${(perimetre - (options.nbc * 2))};
					transform-origin: center;
					animation: tournePetitCercle 1s linear infinite;
				}
				@keyframes tournePetitCercle{
					from {transform: rotate(0deg)}
					to {transform: rotate(360deg)}
				}
			</style>
			</div></div>`
			document.body.insertAdjacentHTML('beforeend', fragCharge);
		}
		if (options.etat === 0) this.supElement('#fond_aff_charge');
	}

	// visuel chargement "ping"
	if (options.typeVisuChargement === 'temps' || options.typeVisuChargement === 'defaut') {
		if (options.etat === 1) {
			window.tempsDebutRequete = Date.now()
		}
		if (options.etat === 0) {
			let tempsFinRequete = Date.now()
			let totalCalculTemps = tempsFinRequete - window.tempsDebutRequete
			if (document.querySelector('#temps-charge-valeur')) {
				document.querySelector('#temps-charge-valeur').innerHTML = totalCalculTemps
			}
		}
	}
}

// obtenir valeur du cookie
export function getCookie(name) {
	var cookieValue = null;
	if (document.cookie && document.cookie !== '') {
		var cookies = document.cookie.split(';');
		for (var i = 0; i < cookies.length; i++) {
			var cookie = cookies[i].trim();
			// Does this cookie string begin with the name we want?
			if (cookie.substring(0, name.length + 1) === (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}
	return cookieValue;
}

//ajax javascript
export function ajax(optionsOrigine, foncOk, foncEr) {
	let couleur_affCharge = '#0F0', largeur_affCharge = 80, rpt_affCharge = 4, nbc_affCharge = 8, epaisseur_affCharge = 8, typeVisuChargement = 'defaut'

	// visuel de chargement
	if (optionsOrigine.attente.largeur != undefined) largeur_affCharge = optionsOrigine.attente.largeur;
	if (optionsOrigine.attente.rpt != undefined) rpt_affCharge = optionsOrigine.attente.rpt;
	if (optionsOrigine.attente.nbc != undefined) nbc_affCharge = optionsOrigine.attente.nbc;
	if (optionsOrigine.attente.couleur != undefined) couleur_affCharge = optionsOrigine.attente.couleur;
	if (optionsOrigine.attente.epaisseur != undefined) epaisseur_affCharge = optionsOrigine.attente.epaisseur
	if (optionsOrigine.attente.typeVisuChargement !== undefined) typeVisuChargement = optionsOrigine.attente.typeVisuChargement

	// etat,largeur,rpt,nbc,epaisseurTrainee,couleur, typeVisuChargement
	let options = {
		etat: 1,
		largeur: largeur_affCharge,
		rpt: rpt_affCharge,
		nbc: nbc_affCharge,
		epaisseur: epaisseur_affCharge,
		couleur: couleur_affCharge,
		// typeVisuChargement: window.ajaxTypeVisuChargement
		typeVisuChargement: typeVisuChargement
	}

	// affiche le visuel d'attente de téléchargement
	sys.affCharge(options)

	let ajaxTelechargeMedia = new XMLHttpRequest()
	ajaxTelechargeMedia.typeVisuChargement = typeVisuChargement

	// fige le format de réponse en json
	if (optionsOrigine.dataTypeReturn === 'json') ajaxTelechargeMedia.responseType = 'json';
	// fige le format de réponse en text
	if (optionsOrigine.dataTypeReturn === 'text') ajaxTelechargeMedia.responseType = 'text';
	// fige le format de réponse en html
	if (optionsOrigine.dataTypeReturn === 'document') ajaxTelechargeMedia.responseType = 'document';

	ajaxTelechargeMedia.nomObjetConteneur = this.nomObjetConteneur;

	// passage de donnéeq à  ajaxTelechargeMedia
	ajaxTelechargeMedia.optionsOrigine = optionsOrigine;

	let ajaxForm = new FormData();
	if (optionsOrigine.asynch !== undefined) optionsOrigine.asynch = true;
	ajaxTelechargeMedia.open(optionsOrigine.type, optionsOrigine.url, true);

	if (optionsOrigine.timeout === undefined) {
		ajaxTelechargeMedia.timeout = 0
	} else {
		ajaxTelechargeMedia.timeout = optionsOrigine.timeout
	}


	ajaxTelechargeMedia.ontimeout = () => {
		console.error('Timeout!!')
	}

	// si csrfToken alors ajoute au header
	if (optionsOrigine.csrfToken) ajaxTelechargeMedia.setRequestHeader('X-CSRFToken', optionsOrigine.csrfToken);

	// pour envoyer du json
	if (optionsOrigine.dataType === 'json') ajaxTelechargeMedia.setRequestHeader('Content-Type', "application/json;charset=UTF-8");

	if (optionsOrigine.credentials == 'true') ajaxTelechargeMedia.withCredentials = true;

	//requête ok
	ajaxTelechargeMedia.onload = function () {
		let infos_status = { code: ajaxTelechargeMedia.status, texte: ajaxTelechargeMedia.statusText };
		// this.optionsOrigine => pour le passage de paramêtres à partir de optionsOrigine(les optionsOrigines de la requête)
		if (ajaxTelechargeMedia.responseType === 'json') {
			foncOk(ajaxTelechargeMedia.response, infos_status) // la réponse est du json
		} else {
			foncOk(ajaxTelechargeMedia.responseText, infos_status)
		}
	};

	// éfface le visuel d'attente de téléchargement
	ajaxTelechargeMedia.onloadend = () => {
		if (optionsOrigine.attente.garderTemointDeCharge === undefined) {
			sys.affCharge({ etat: 0, typeVisuChargement: ajaxTelechargeMedia.typeVisuChargement })
		}
	}

	//requête erreur
	ajaxTelechargeMedia.onerror = function (er) {
		if (foncEr === undefined) {
			console.log('Fonction erreur non définie, status: ' + er.target.status)
		} else {
			foncEr(er.target.status)
		}
		// send message netWorkOffLine
		if (window.navigator.onLine === false) {
			document.dispatchEvent(new CustomEvent('netWorkOffLine', {}))
		}
	}

	//prépare le formulaire
	if (optionsOrigine.data !== undefined) {
		// json
		if (optionsOrigine.dataType === 'json') {
			ajaxTelechargeMedia.send(JSON.stringify(optionsOrigine.data));
		}
		// pour envoyer un formulaire
		if (optionsOrigine.dataType === 'form') {
			for (var key in optionsOrigine.data) {
				ajaxForm.append(key, optionsOrigine.data[key]);
			}
			ajaxTelechargeMedia.send(ajaxForm);
		}
	} else {
		ajaxTelechargeMedia.send('');
	}
}


export function validerInfosCookie() {
	let requete = {
		type: "post",
		url: "valider_retourInfoCookie",
		data: {}
	};
	sys.ajax(requete, function (infos) {
		//gui.debug('système:validerInfosCookie',infos);
		console.log('ok pour infos cookie!');
		document.querySelector('#retourInfosCookieBureau').style.display = 'none';
		document.querySelector('#retourInfosCookieMobile').style.display = 'none';
	});
}

//première lettre en majuscule
export function majusculePremiere(mot) {
	return mot[0].toUpperCase() + mot.substring(1, mot.length);
}


//ajouter un évènement
export function addEvent(element, action, fonction, etat) {
	//'id' ou 'class'
	let testTypeEle = element.substr(0, 1);
	if (testTypeEle != '#' && testTypeEle != '.') console.log('Type élément inconnu (manque # ou .) !');
	//id
	if (document.querySelector(element) != null && testTypeEle == '#') {
		document.querySelector(element).addEventListener(action, fonction, etat);
	}
	//class
	if (document.querySelectorAll(element)[0] != null && testTypeEle == '.') {
		let elements = document.querySelectorAll(element);
		for (const sysEle of elements) {
			sysEle.addEventListener(action, fonction, etat);
		}
	}
}

//genere une chaine decaratère pour le débug
export function genChaine(nbc) {
	let idc = 1, repId = 1, chaine = '';
	for (let i = 1; i < parseInt(nbc) + 1; i++) {
		chaine += 'X';
		if (idc == 9) {
			i++;
			chaine += repId.toString();
			repId++;
			idc = 0;
		}
		idc++
	}
	return chaine;
}

//supprimer les accents
export function supAccents(chaine) {
	let accents = 'àáâãäåÀÁÂÃÄÅçÇÐèéêëÈÉÊËìíîïÌÍÎÏñÑòóôõöÒÓÔÕÖùúûüÙÚÛÜýÿÝŸ';
	let sansAccents = 'aaaaaaAAAAAAcCDeeeeEEEEiiiiIIIInNoooooOOOOOuuuuUUUUyyYY'
	let nbc = chaine.length;
	let nouv = '';
	for (let i = 0; i < nbc; i++) {
		let idc = accents.indexOf(chaine[i]);
		if (idc >= 0) {
			nouv += sansAccents[idc];
		} else {
			nouv += chaine[i];
		}
	}
	return nouv;
}

//formate le nom d'une fonction
export function formatNomFonc(chaine) {
	chaine = this.supAccents(chaine);
	let caracSpe = '&~#"\'`^@[](){}$ê£*³µ!§œ|\\/:;.*';
	let nbc = chaine.length;
	let nouv = '';
	for (let i = 0; i < nbc; i++) {
		let idc = caracSpe.indexOf(chaine[i]);
		if (idc == -1) {
			let carac = chaine[i];
			if (chaine[i] == "-") carac = '_';
			nouv += carac;
		}
	}
	return nouv;
}

export function heureText() {
	let h, m, s;
	let d = new Date();
	let heure = d.getHours();
	let minutes = d.getMinutes();
	let secondes = d.getSeconds();
	if (heure.toString().length == 1) h = '0' + heure;
	if (heure.toString().length > 1) h = heure;
	if (minutes.toString().length == 1) m = '0' + minutes;
	if (minutes.toString().length > 1) m = minutes;
	if (secondes.toString().length == 1) s = '0' + secondes;
	if (secondes.toString().length > 1) s = secondes;
	return h + ':' + m + ':' + s
}

//format la date en text
export function dateText() {
	var leJour, leMois;
	var laDate = new Date();
	var leJourI = laDate.getDate();
	if (leJourI.toString().length == 1) leJour = '0' + leJourI;
	if (leJourI.toString().length > 1) leJour = leJourI;
	var leMoisI = laDate.getMonth() + 1;
	if (leMoisI.toString().length == 1) leMois = '0' + leMoisI;
	if (leMoisI.toString().length > 1) leMois = leMoisI;
	return leJour + '/' + leMois + "/" + laDate.getFullYear();
}


//dump
export function dump(element) {
	for (let key in element) {
		if (element[key] != null) console.log(key + " -> " + element[key]);
	}
}

export function recupNomImageBackground(idElement) {
	var tempoImage1 = document.querySelector('#' + idElement).style.backgroundImage;
	var r1 = tempoImage1.indexOf('"') + 1;
	var r2 = tempoImage1.lastIndexOf('"');
	let tempoImage2 = tempoImage1.substring(r1, r2);
	var r3 = tempoImage2.lastIndexOf('/') + 1
	return tempoImage2.substr(r3, tempoImage2.length - r3);
}

//touche entrée simule un clique sur un élément grace à son id
export function rigEnter(ev, idActiveur, idAactiver) {
	var cl = ev.keyCode;
	if (cl == 13 && document.activeElement.id == idActiveur) {
		var eleToClick = document.querySelector("#" + idAactiver);
		eleToClick.click();
	}
}

// plein écran
export function fullscreen(elem) {
	if (elem.requestFullscreen) {
		elem.requestFullscreen();
	} else if (elem.msRequestFullscreen) {
		elem.msRequestFullscreen();
	} else if (elem.mozRequestFullScreen) {
		elem.mozRequestFullScreen();
	} else if (elem.webkitRequestFullscreen) {
		elem.webkitRequestFullscreen();
	}
}

// sortie du plein écran
export function exitFullscreen() {
	if (document.exitFullscreen) {
		document.exitFullscreen();
	} else if (document.mozCancelFullScreen) {
		document.mozCancelFullScreen();
	} else if (document.webkitExitFullscreen) {
		document.webkitExitFullscreen();
	}
}

//déterminer la résolutiion de l'écran en X(largeur)
export function estResolution() {
	let Eresolution
	Xresolution = 320
	let mq = window.matchMedia("(min-width: 500px)");
	if (mq.matches) {
		Eresolution = 500;
		if (Eresolution > Xresolution) Xresolution = Eresolution;
	}

	mq = window.matchMedia("(min-width: 700px)");
	if (mq.matches) {
		Eresolution = 700;
		if (Eresolution > Xresolution) Xresolution = Eresolution;
	}

	mq = window.matchMedia("(min-width: 900px)");
	if (mq.matches) {
		Eresolution = 900;
		if (Eresolution > Xresolution) Xresolution = Eresolution;
	}

	mq = window.matchMedia("(min-width: 1280px)");
	if (mq.matches) {
		Eresolution = 1280;
		if (Eresolution > Xresolution) Xresolution = Eresolution;
	}
	//console.log('X -> '+Xresolution);
	return Xresolution;
}

/**
 * Passer un object javascript à un attribut html
 *@param {object} obj = objet à transmettre au html
 *@return {string}
 */
export function data_in_att(obj) {
	// TODO: vérifier que c'est un objet, si non log un message
	return escape(JSON.stringify(obj));
}

/**
 * Afficher / rendre visible une liste d'élément html
 * Attention, vous devez spécifier le type de l'élémnet: flex, block, ...
 *@param {array} liste , exemple ['.classe-ele1,flex', '#chemin,block', ...]
 */
export function afficherElements(liste) {
	// console.log('-> fonction afficherElements !')
	for (let i = 0; i < liste.length; i++) {
		let item = liste[i].split(',')
		let ele = item[0]
		let affichage = item[1]
		// class
		if (ele[0] === '.') {
			let eles = document.querySelectorAll(ele)
			for (let i = 0; i < eles.length; i++) {
				let ele = eles[i]
				ele.style.display = affichage
			}
		}
		// id
		if (ele[0] === '#') {
			document.querySelector(ele).style.display = affichage
		}
	}
}

/**
 * Effacer / rendre invisible une liste d'élément html
 *@param {array} liste , exemple ['.classe-ele1', '#chemin', ...]
 */
export function effacerElements(liste) {
	for (let i = 0; i < liste.length; i++) {
		let item = liste[i]
		// class
		if (item[0] === '.') {
			let eles = document.querySelectorAll(item)
			for (let i = 0; i < eles.length; i++) {
				let ele = eles[i]
				ele.style.display = 'none'
			}
		}
		// id
		if (item[0] === '#') {
			document.querySelector(item).style.display = 'none'
		}
	}
}

/**
 * Test array permissions
 * @param {Array<string>} list global function names list
 * @return {Boolean} true or false
 */
export async function testArrayPermissions(list) {
	let retour = true
	for (let i = 0; i < list.length; i++) {
		const func = list[i];
		retour = await window[func]()
	}
	return retour
}
