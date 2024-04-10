const fs = require('fs')
const path = require('path')
const { dialog, ipcMain, session, app, Menu, getCurrentWindow, protocol, globalShortcut, BrowserWindow } = require('electron')
process.env['ELECTRON_DISABLE_SECURITY_WARNINGS'] = 'true'

let win, winC
// url à tester
let urlTester = 'http://django-local.org:8001/wv/login_hardware'

function infosApp() {
  let frag = `<div class="l100p BF-ligne popup-titre1">Infos application :</div>`
  for (const dependency of ['chrome', 'node', 'electron']) {
    frag += `<div class="l100p BF-ligne popup-msg1">${dependency}-version : ${ process.versions[dependency] }</div>`
  }
  win.webContents.send('popup', frag)
}

function chargerTest() {
  let nomFichier = dialog.showOpenDialogSync(win, {
    properties: ['openFile'],
    title: "Charger un test",
    defaultPath: __dirname,
    filters: { filtres: [{ name : 'Tests', extensions: ['json'] }] }
  })[0]
  console.log('nomFichier = ', nomFichier)
  if (nomFichier !== undefined) {
    try {
      const fic =  fs.readFileSync(nomFichier, 'utf8')
      win.webContents.send('afficherFichierTest',fic)
    } catch (erreur) {
      console.log(`erreur chagement fichier, ${ erreur }`)
    }
  } else {
    console.log('Erreur dans le choix du fichier à charger !')
  }
}

// ouvre la boite de dialogue pour donner un nom au fichier à sauvegarder
function demandeerSauvegarde() {
  let nomFichier = dialog.showSaveDialogSync(win, {
    properties: ['openFile'],
    title: "Sauver le test",
    defaultPath: __dirname,
    filters: { filtres: [{ name : 'Tests', extensions: ['json'] }] }
  })
  if (nomFichier !== undefined) {
    win.webContents.send('demandeDonneesPourSauvegarde', nomFichier)
  } else {
    console.log('Erreur dans le nom de fichier à sauvegarder !')
  }
}


const template = [
  { label: 'Fichier', submenu: [
      { label: 'Sauver', click : demandeerSauvegarde },
      { label: 'Charger', click : chargerTest }
    ]
  },
  { label: 'Test', submenu : [
      { label: 'Nouveau', click : () => {
          win.webContents.send('test', 'nouveau')
        }
      },
      { label: 'Lancer', click : () => {
          win.webContents.send('test', 'demandeLancerTests')
        }
      }
    ]
  },
  { label: 'Aide', submenu : [
      { label: 'A propos', click : infosApp }
    ]
  }
]

const menu = Menu.buildFromTemplate(template)
//Menu.setApplicationMenu(menu)

function createWindow () {
  win = new BrowserWindow({
    width: 1200,
    height: 1200,
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true
    }
  })

  win.webContents.openDevTools()

  win.setMenu(menu)
  console.log(path.resolve(path.join(`${ __dirname }/admin`, 'index.html')))
  win.loadFile('./adminTests/index.html')
}

function creationFenetreSiteVisite() {
  winSiteVisite = new BrowserWindow({
    parent: win,
    width: 1200,
    height: 1200,
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true,
      preload: path.resolve(path.join(`${ __dirname }/`, "preloadSiteVisite.js"))
    }
  })

  winSiteVisite.webContents.clearHistory()
  winSiteVisite.webContents.openDevTools()

  winSiteVisite.setMenu(null)

  winSiteVisite.loadURL(
    urlTester,
    { userAgent: '{"hostname":"phenixElectron", "token": "$a;b2yuM5454@4!cd", "password":"PQVot?TKFzSvjmkY", "modeNfc":"NFCLO", "front":"FOR", "ip":"192.168.1.4"}' }
  )
}

ipcMain.on('donneesJsonPourSauvegarde', (event, donnees) => {
  console.log('json à sauvegarder dans un fichier= ', JSON.stringify(donnees.data, null, 4))
  fs.writeFileSync(donnees.nomFichier, JSON.stringify(donnees.data,null,'\t'), 'utf8')
})

ipcMain.on('donneesJsonPourLancerTests', (event, donnees) => {
  console.log('tests(json) à lancer = ', donnees)
  winSiteVisite.webContents.send('demandeLancerTests',donnees)
})


app.on('window-all-closed', function () {
if (process.platform !== 'darwin') app.quit()
})

app.whenReady().then(() => {
  /*
  // redirection
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    // redirection
    if (details.url.indexOf('lecteur_nfc.js') > 0) {
      console.log('details = ', details)
      callback({cancel: false, redirectURL: `http://django-local.org:8001/static/webview/electron_proj1/besoinTests.js`})
    } else {
      return callback({})
    }
  })
   */

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })

  // raccourcis: recharge page
  globalShortcut.register('CommandOrControl+P', () => {
    win.reload()
  })
  globalShortcut.register('CommandOrControl+R', () => {
    winSiteVisite.reload()
  })

  createWindow()
  win.maximize()
  creationFenetreSiteVisite()
  winSiteVisite.maximize()

})
