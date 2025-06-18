/**
 * Show setting printer UI
 */
window.settingsShowPrinter = function () {
  // changer titre
  vue_pv.asignerTitreVue(`<span data-i8n="settings,capitalize">Paramètres</span> - <span data-i8n="logs",capitalize">Logs</span>`)

  let template = `
  <div class="BF-col-deb l100p h100p" style="font-size: 1.5rem">
    <button>Test printer</button>
    <label>Bluetooth enable</label>
    <label>Bluetooth available</label>
    <label>Bluetooth connection</label>
    <label>Bluetooth write</label>
  </div>`

  document.querySelector('.content-settings').innerHTML = template
}


/*

 // create print sunmi queue
        if (window.sunmiPrintQueue === undefined) {
          window.sunmiPrintQueue = []
        }
 const options = { printUuid: sys.uuidV4(), content: data.data }
sunmiPrintQueue.push(options)
await bluetoothWrite(options.printUuid)
*/