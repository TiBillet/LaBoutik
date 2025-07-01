window.SettingsTestPrint = async function () {
  try {
    // init led
    document.querySelector('#Bluetooth-write-result').setAttribute('class', 'led-red settings-led-size')

    // create print sunmi queue
    if (window.sunmiPrintQueue === undefined) {
      window.sunmiPrintQueue = []
    }

    // load function bluetoothWrite
    const { bluetoothWrite } = await import("../../modules/mobileDevice.js")

    // date
    const date = new Date()
    const formattedDatePart1 = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${(date.getDate()).toString().padStart(2, '0')} `
    const formattedDatePart2 = `${(date.getHours()).toString().padStart(2, '0')}:${(date.getMinutes()).toString().padStart(2, '0')}:${(date.getSeconds()).toString().padStart(2, '0')} `
    const formattedDate = formattedDatePart1 + ' ' + formattedDatePart2

    // print
    const content = [
      { type: "font", value: "A" },
      { type: "size", value: 1 },
      { type: "bold", value: 1 },
      { type: "align", value: "left" },
      { type: "text", value: "** TEST PRINT **" },
      { type: "bold", value: 0 },
      { type: "text", value: "Hello World" },
      { type: "size", value: 0 },
      { type: "text", value: "--------------------------------" },
      { type: "text", value: `Test completed at ${formattedDate}` },
      { type: "feed", value: 2 },
      { type: "cut" }
    ]

    const options = { printUuid: sys.uuidV4(), content }
    sunmiPrintQueue.push(options)
    const result = await bluetoothWrite(options.printUuid)

    if (result) {
      document.querySelector('#Bluetooth-write-result').setAttribute('class', 'led-green settings-led-size')
    } else {
      document.querySelector('#Bluetooth-write-result').setAttribute('class', 'led-red settings-led-size')
    }

  } catch (error) {
    console.log('-> SettingsTestPrint,', error)
  }
}

/**
 * Show setting printer UI
 */
window.settingsShowPrinter = async function () {
  // load function bluetoothWrite
  const { bluetoothSerialAvailable, enableBluetooth, bluetoothConnection } = await import("../../modules/mobileDevice.js")
  const bluetoothAvailable = await bluetoothSerialAvailable() === true ? 'led-green' : 'led-red'
  const bluetoothEnable = await enableBluetooth() === true ? 'led-green' : 'led-red'
  const bluetoothConnected = await bluetoothConnection() === true ? 'led-green' : 'led-red'

  // changer titre
  vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="logs",capitalize">Logs</span>`)

  const style = `
  <style>
    .settings-fond {
      width: 100%;
      height: 100%;
      font-size: 1.5rem;
      --settings-container-led-size: 30px;
      --settings-state-line-size: 4%;
      --settings-led-size: 10px;
      display: flex;
      flex-direction: column;
      justify-content: start;
      align-items: center;

    }

    .settings-state-content-step {
        width: 100%;
        height: var(--settings-container-led-size);
        display: flex;
        flex-direction: row;
        justify-content: center;
        align-items: center;
        margin: 0;
        padding: 0;
    }

    .settings-state {
        width: var(--settings-container-led-size);
        height: var(--settings-container-led-size);
        border-radius: 50%;
        border: 2px solid var(--blanc01);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin: 0;
        padding: 0;
    }

    .settings-state-line {
        width: var(--settings-state-line-size);
        height: 2px;
        border: 1px solid var(--blanc01);
        margin: 0 4px;
    }

    .settings-label {
        width: 30%;
        color: var(--blanc01);
    }

    .settings-led-size {
        width: var(--settings-led-size);
        height: var(--settings-led-size);
    }

    .settings-state-connexion-line {
        width: calc(var(--settings-container-led-size) + var(--settings-state-line-size) + 30%);
        height: 20px;
        border-left: 2px solid var(--blanc01);
        transform : translate(calc(var(--settings-container-led-size) / 2 - 4px));
    }
  </style>`

  let template = `
  <div class="settings-fond">
    <bouton-basique traiter-texte="1" texte="TEST IMPRESSION|1.5rem||testPrinting-uppercase" couleur-fond="#0335b8"  width="240px" height="100px"  onclick="SettingsTestPrint();" style="margin: 30px 0;"></bouton-basique>
  
     <div class="settings-state-content-step">
      <div class="settings-state">
        <div class="${bluetoothAvailable} settings-led-size"></div>
      </div>
      <div class="settings-state-line"></div>
      <label class="settings-label">Bluetooth ${getTranslate('available')}</label>
    </div>

    <div class="BF-ligne l100p">
      <div class="settings-state-connexion-line"></div>
    </div>

    <div class="settings-state-content-step">
      <div  class="settings-state">
        <div class="${bluetoothEnable} settings-led-size"></div>
      </div>
      <div class="settings-state-line"></div>
      <label class="settings-label">Bluetooth ${getTranslate('enable')}</label>
    </div>

    <div class="BF-ligne l100p">
      <div class="settings-state-connexion-line"></div>
    </div>

    <div class="settings-state-content-step mb8px">
      <div class="settings-state">
        <div class="${bluetoothConnected} settings-led-size"></div>
      </div>
      <div class="settings-state-line"></div>
      <label class="settings-label">Bluetooth ${getTranslate('connection')}</label>
    </div>

    <div class="BF-ligne l100p">
      <div class="settings-state-connexion-line"></div>
    </div>

    <div class="settings-state-content-step mb8px">
      <div class="settings-state">
        <div id="Bluetooth-write-result" class="led-red settings-led-size"></div>
      </div>
      <div class="settings-state-line"></div>
      <label class="settings-label">Bluetooth ${getTranslate('printing')}</label>
    </div>
  </div>`

  document.querySelector('.content-settings').innerHTML = style + template
}