console.log('login_hardware.js')
import { generatePemKeys, signMessage } from '/static/webview/js/modules/cryptoRsa.js'
import { translate, getTranslate } from '/static/webview/js/modules/i8n.js'
import { isCordovaApp, cordovaReadFileJson, cordovaWriteToFile } from './modules/mobileDevice.js'

const PORT = 3000
const mobile = isCordovaApp()
const cordovaFileName = 'configLaboutik.json'

// get configuration save in localstorage
let confLocalStorage = JSON.parse(localStorage.getItem('laboutik'))

// read configuration file from pi or desktop
async function readFromFile() {
  try {
    const response = await fetch(`http://localhost:${PORT}/config_file`, {
      method: "GET",
      mode: 'cors'
    })
    return await response.json()
  } catch (error) {
    console.log('readFromFile,', error)
    return null
  }
}

async function writeConfigFile(configuration) {
  try {
    const response = await fetch(`http://localhost:${PORT}/write_config_file`, {
      method: "POST",
      mode: 'cors',
      body: JSON.stringify(configuration)
    })
    const retour = await response.json()
    return retour.status
  } catch (error) {
    console.log('writeConfigFile,', error)
    return false
  }
}


// delete local configuration and update configuration app
async function deleteConfs() {
  console.log('-> deleteConfs')
  try {
    // supprimer le fichier de configuration local
    localStorage.removeItem('laboutik')

    let configuration, basePath, pathToFile, updateFile
    if (mobile === true) {
      basePath = cordova.file.dataDirectory
      pathToFile = basePath + cordovaFileName
      configuration = await cordovaReadFileJson(pathToFile)
    } else {
      configuration = await readFromFile()
    }


    // supprimer le serveur courant
    configuration.current_server = ''

    // supprimer le serveur courant sauvegardé dans configuration.servers
    const serversToKeep = configuration.servers.filter(item => item.server !== configuration.current_server)
    configuration['servers'] = serversToKeep
    // supprimer le clientformData.append('ip_lan', configuration.ip)
    configuration.client = null

    // sauvegarder le fichier de configuration app
    if (mobile === true) {
      updateFile = await cordovaWriteToFile(basePath, cordovaFileName, configuration)
    } else {
      updateFile = await writeConfigFile(configuration)
    }
    if (updateFile === true) {
      return true
    } else {
      return false
    }
  } catch (error) {
    console.log('Erreur, deleteConfs :', error)
    return false
  }
}

window.cashlessNewPair = async function () {
  const result = await deleteConfs()
  let redirectionUrl = `http://localhost:${PORT}`
  if (mobile === true) {
    redirectionUrl = 'http://localhost/index.html'
  }
  console.log('result =', result)
  if (result === true) {
    // redirection
    window.location.href = redirectionUrl
  } else {
    console.log('newPair, erreur maj configuration')
  }
}

function showPairAgain() {
  localStorage.removeItem('laboutik')
  document.querySelector('#fond-contenu').innerHTML += `<div class="BF-col l100p h100p" style="background-color:#0000FF;color:#FFFFFF;" onclick="cashlessNewPair();">
    <h1 data-i8n="pairAgainAndClick,capitalize" style="white-space: pre-line;text-align: center;">Faire un nouvel appairage\net cliquer !</h1>
  </div>`
  translate('#fond-contenu')
}

async function initLogin() {
  console.log('-> initLogin')

  const configuration = JSON.parse(localStorage.getItem('laboutik'))
  console.log('-> configuration =', configuration)
  if (configuration !== null) {
    const csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]').value
    const signature = await signMessage(configuration.keysPemCashlessClient, configuration.password)

    const formData = new FormData()
    formData.append('username', configuration.client.username)
    formData.append('password', configuration.client.password)
    formData.append('periph', configuration.front_type)
    formData.append('signature', signature.b64encoded)
    if (mobile === true) {
      formData.append('ip_lan', configuration.ip)
    } else {
      formData.append('ip_lan', configuration.piDevice.ip)
    }


    const response = await fetch(configuration.current_server + 'wv/login_hardware/', {
      headers: {
        Accept: 'application/json',
        'X-CSRFToken': csrf_token
      },
      mode: 'cors',
      method: 'POST',
      body: formData
    })
    // ok
    if (response.status === 200) {
      let url = configuration.current_server + 'wv'
      window.location.href = url
    }


    // console.log('response =', response)
    if (response.status === 400 || response.status === 401) {
      document.querySelector('#fond-contenu').innerHTML += `<div class="BF-col l100p h100p" style="background-color:#0000FF;color:#FFFFFF;" onclick="cashlessNewPair();">
        <h1 data-i8n="deviceDisabledDeletedPairAgain,capitalize" style="white-space: pre-line;text-align: center;">Appareil désactivé ou supprimé.\nFaire un nouvel appairage\net cliquer !</h1>
      </div>`
      translate('#fond-contenu')
    }
  } else {
    showPairAgain()
  }
}


async function activateDevice(configuration) {
  console.log('-> activateDevice, configuration =', configuration)
  const configServer = configuration.servers.find(item => item.server === configuration.current_server)

  try {
    // get csrf token 
    const csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]').value

    // generate client rsa keys pem
    const keysPemCashlessClient = await generatePemKeys()
    // add to configuration
    configuration['keysPemCashlessClient'] = keysPemCashlessClient

    const formData = new FormData()

    // payload
    formData.append('version', configuration.version)
    formData.append('username', configuration.client.username)
    formData.append('password', configuration.client.password)
    formData.append('hostname', configuration.hostname)
    formData.append('periph', configuration.front_type)
    formData.append('public_pem', configuration.keysPemCashlessClient.publicKey)
    formData.append('pin_code', configuration.pin_code)
    if (mobile === true) {
      formData.append('ip_lan', configuration.ip)
    } else {
      formData.append('ip_lan', configuration.piDevice.ip)
    }


    const response = await fetch(configuration.current_server + 'wv/new_hardware/', {
      headers: {
        Accept: 'application/json',
        'X-CSRFToken': csrf_token
      },
      mode: 'cors',
      method: 'POST',
      body: formData
    })
    const retour = await response.json()
    // console.log('retour =', retour)
    if (response.status === 201) {
      // save config app in local storage
      console.log('new_hardware ok, configuration =', configuration)
      localStorage.setItem('laboutik', JSON.stringify(configuration))
      console.log("-> ActivateDevice, 'wv/new_hardware'")
      initLogin()
    }

    if (response.status === 400) {
      showPairAgain()
    }
  } catch (error) {
    console.log('-> ActivateDevice,', error)
  }
}

// main
function initMain(configuration) {
  console.log('-> initMain, configuration =', configuration)

  // lecture fichier de conf ok
  if (configuration !== null) {

    // reset confLocalStorage si "login retour" !== "login confLocalStorage"
    if (confLocalStorage !== null && (configuration.client.password !== confLocalStorage.client.password || configuration.client.username !== confLocalStorage.client.username)) {
      localStorage.removeItem('laboutik')
      confLocalStorage = null
    }

    // login error = client null ou pas de serveur courant désigné
    if (configuration.client === null || configuration.current_server === "") {
      // nouvel appairage
      showPairAgain()
      return
    }

    // la configuration local n'existe pas
    if (confLocalStorage === null) {
      // console.log('. confLocalStorage = null => activateDevice()')
      activateDevice(configuration)
      return
    }

    initLogin()
  }
}

try {
  Sentry.init({
    dns: "https://677e4405e6f765888fdec02d174000d6@o262913.ingest.us.sentry.io/4506881155596288",
    tracesSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  })
} catch (error) {
  console.log('sentry :', error)
}

// mobile
if (mobile === true) {
  document.addEventListener('deviceready', async () => {
    console.log('-> mobile, deviceready')
    const basePath = cordova.file.dataDirectory
    const pathToFile = basePath + cordovaFileName

    // read configuration file
    const configuration = await cordovaReadFileJson(pathToFile)
    initMain(configuration)
  })
} else {
  // pi, desktop

  // read configuration file
  const configuration = await readFromFile()
  initMain(configuration)
}
