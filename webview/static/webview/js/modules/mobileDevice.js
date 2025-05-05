// source : https://github.com/don/BluetoothSerial?tab=readme-ov-file
// source : https://github.com/neodynamic/js-escpos-builder

/**
 * Cordova add
 * @module ./modules/mobileDevice.js
 */


/**
 * read a file an convert it in Json object
 * @public
 * @param {string} pathToFile - path file to read
 * @returns {JSON | null}
 */
export async function cordovaReadFileJson(pathToFile) {
  // console.log('-> cordovaReadFileJson, pathToFile =', pathToFile)
  const promiseReadFromFile = new Promise((resolve) => {
    try {
      window.resolveLocalFileSystemURL(pathToFile, function (fileEntry) {
        fileEntry.file(function (file) {
          const reader = new FileReader()
          reader.onloadend = function (e) {
            resolve(JSON.parse(this.result))
          }
          reader.readAsText(file)
        }, () => { resolve(null) })
      }, () => { resolve(null) })
    } catch (error) {
      console.log('-> cordovaReadFromFile,', error)
      resolve(null)
    }
  })
  return await promiseReadFromFile
}


/**
 * Write configuration file
 * @param {string} basePath - path
 * @param {string} saveFileName - file name
 * @param {object} rawData - content file
 * @returns {boolean}
 */
export async function cordovaWriteToFile(basePath, saveFileName, rawData) {
  // console.log('-> writeToFile, saveFileName =', saveFileName, '  --  basePath =', basePath)
  const data = JSON.stringify(rawData)

  const promiseWiteToFile = new Promise((resolve) => {
    window.resolveLocalFileSystemURL(basePath, function (directoryEntry) {
      directoryEntry.getFile(saveFileName, { create: true },
        function (fileEntry) {
          fileEntry.createWriter(function (fileWriter) {
            fileWriter.onwriteend = function (e) {
              // console.log('info , write of file "' + saveFileName + '" completed.')
              resolve(true)
            }
            fileWriter.onerror = function (e) {
              // you could hook this up with our global error handler, or pass in an error callback
              console.log('info, write failed: ' + e.toString())
            }
            const blob = new Blob([data], { type: 'text/plain' })
            fileWriter.write(blob)
          }, () => { resolve(false) })
        }, () => { resolve(false) })
    }, () => { resolve(false) })
  })
  return await promiseWiteToFile
}

/**
 * Is cordova application ?
 * @public
 * @returns {boolean}
 */
export function isCordovaApp() {
  try {
    if (cordova) {
      return true
    }
  } catch (error) {
    return false
  }
}

export async function enableBluetooth() {
  return await new Promise((resolve, reject) => {
    window.bluetoothSerial.enable(
      function () {
        console.log("Bluetooth is enabled");
        resolve(true)
      },
      function () {
        console.log("The user did *not* enable Bluetooth");
        reject(false)
      }
    );
  })

}

export async function bluetoothSerialAvailable() {
  return await new Promise((resolve) => {
    try {
      window.bluetoothSerial.available(() => {
        // console.log('-> bluetoothSerialAvailable =  succès')
        resolve(true)
      }, () => {
        // console.log('-> bluetoothSerialAvailable =  no')
        resolve(false)
      })
    } catch (error) {
      resolve(false)
    }
  })
}



export async function bluetoothGetMacAddress(name) {
  let retour = 'unknown'
  const testBluetoothSerialAvailable = await bluetoothSerialAvailable()
  // console.log('testBluetoothSerialAvailable =', testBluetoothSerialAvailable)

  if (testBluetoothSerialAvailable) {
    const list = await new Promise((resolve) => {
      // list devices
      window.bluetoothSerial.list(function (devices) {
        resolve(devices)
      }, (error) => {
        console.log('error =', error);
        resolve([])
      });
    })

    for (let i = 0; i < list.length; i++) {
      const device = list[i];
      if (device.name === name) {
        retour = device.id
        break
      }
    }
  }
  return retour
}

async function loadAndConvertImageToB64(url) {
  const load = await new Promise((resolve) => {
    try {
      let img = new Image()
      img.src = url
      img.onload = () => {
        let canvas = document.createElement('canvas')
        let ctx = canvas.getContext('2d')
        canvas.height = img.naturalHeight;
        canvas.width = img.naturalWidth;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const base64String = canvas.toDataURL('image/png')
        resolve(base64String)
      }
    } catch (error) {
      console.log('-> loadAndConvertImageToB64,', error)
      resolve(null)
    }
  })
  return load
}

async function escPosImageLoad(url) {
  return await new Promise(async (resolve) => {
    try {
      const escpos = Neodynamic.JSESCPOSBuilder
      const imageB64 = await loadAndConvertImageToB64(url)
      escpos.ESCPOSImage.load(imageB64).then(image => {
        resolve(image)
      })
    } catch (error) {
      console.log('-> EscPosImageLoad,', error)
      resolve(null)
    }
  })
}


/**
 * async bluetooth connect
 * @param {string} macAddress 
 * @returns 
 */
async function bluetoothConnect(macAddress) {
  const test = await new Promise((resolve) => {
    window.bluetoothSerial.connect(macAddress, async (result) => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothConnect, error = ${error}`)
    })
  })
  return test
}

/**
 * async bluetooth is connected
 */
async function bluetoothIsConnected() {
  const test = await new Promise((resolve) => {
    window.bluetoothSerial.isConnected(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
    })
  })
  return test
}


async function bluetoothSerialWrite(contentToWrite) {
  const write = await new Promise((resolve) => {
    window.bluetoothSerial.write(contentToWrite, () => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothSerialWrite, error = ${error}`)
    })
  })
  return write
}

async function bluetoothDisconnect() {
  const disconnect = await new Promise((resolve) => {
    window.bluetoothSerial.disconnect(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothDisconnect, error = ${error}`)
    })
  })
  return disconnect
}

export async function bluetoothConnection() {
  let connect = false
  console.log('-> bluetoothConnection -', new Date())

  const macAddress = await bluetoothGetMacAddress("InnerPrinter")
  const isConnected = await bluetoothIsConnected()

  if (isConnected === false) {
    connect = await bluetoothConnect(macAddress)
  } else {
    connect = true
  }

  // tentative de reconnexion après 2 secondes
  if (connect === false) {
    setTimeout(bluetoothConnection, 2 * 1000)
  }
}


/**
 * Print command
 * @param {String} currentPrintUuid 
 */
export async function bluetoothWrite(currentPrintUuid) {
  // 1- imppression courante
  console.log(`--------------------------  ${currentPrintUuid}  -----------------------------`);
  console.log(`1 -> bluetoothWrite, sunmiPrintQueue =`, sunmiPrintQueue)
  const currentPrint = sunmiPrintQueue.find(queue => queue.printUuid === currentPrintUuid)
  const content = currentPrint.content

  // 2 - interprets and print
  await bluetoothConnection()
  console.log('-> Après bluetoothConnection')

  const escpos = Neodynamic.JSESCPOSBuilder
  const escposCommands = new escpos.Document()
  // fonte par défaut
  escposCommands.font(escpos.FontFamily.A)
  window.escpos = escpos  // dev
  // process data
  for (let i = 0; i < content.length; i++) {
    const line = content[i]

    // image
    if (line.type === 'image') {
      const image = await escPosImageLoad(line.value)
      escposCommands.image(image, escpos.BitmapDensity.D24)
    }

    // text
    if (line.type === 'text') {
      escposCommands.text(line.value)
    }

    // barcode
    if (line.type === 'barcode') {
      escposCommands.linearBarcode(line.value, escpos.Barcode1DType.EAN13, new escpos.Barcode1DOptions(2, 100, true, escpos.BarcodeTextPosition.Below, escpos.BarcodeFont.A))
    }

    // qrcode
    if (line.type === 'qrcode') {
      escposCommands.qrCode(line.value, new escpos.BarcodeQROptions(escpos.QRLevel.L, 6))
    }

    // size
    if (line.type === 'size') {
      escposCommands.size(line.value, line.value)
    }

    // align
    if (line.type === 'align') {
      let result = escpos.TextAlignment.Center
      if (line.value === "left") {
        result = escpos.TextAlignment.LeftJustification
      }
      if (line.value === "right") {
        result = escpos.TextAlignment.RightJustification
      }
      escposCommands.align(result)
    }

    // font
    if (line.type === 'font') {
      if (line.value === "A") {
        escposCommands.font(Neodynamic.JSESCPOSBuilder.FontFamily.A)
      }
      if (line.value === "B") {
        escposCommands.font(Neodynamic.JSESCPOSBuilder.FontFamily.B)
      }
      if (line.value === "C") {
        escposCommands.font(Neodynamic.JSESCPOSBuilder.FontFamily.C)
      }
    }

    // ne fonctionne pas
    // bold
    //  if (line.type === 'bold') {
    //   if (line.value === 1) {
    //     console.log('-> bold =', escpos.FontStyle.Bold)

    //     escposCommands.style([escpos.FontStyle.Bold])
    //   } else {
    //     escposCommands.style([])
    //   }
    // }
    //

    // feed
    if (line.type === 'feed') {
      escposCommands.feed(line.value)
    }

    // cut
    if (line.type === 'cut') {
      escposCommands.cut()
    }
  }

  const result = escposCommands.generateUInt8Array()
  const rPrint = await bluetoothSerialWrite(result)
  console.log('-> bluetoothSerialWrite =', rPrint)

  // 3 - enlever l'impression faite de la queue d'impression
  if (rPrint) {
    sunmiPrintQueue = sunmiPrintQueue.filter(queue => queue.printUuid !== currentPrintUuid)
  }
  console.log("2 - sunmiPrintQueue ", sunmiPrintQueue)

  // 4 - boucler sur la queue d'impression si non vide
  if (sunmiPrintQueue.length > 0) {
    await bluetoothWrite(sunmiPrintQueue[0])
  }

  await bluetoothDisconnect()
}

export async function bluetoothOpenCashDrawer() {
  await bluetoothConnection()

  let data = new Uint8Array(5)
  data[0] = 0x10
  data[1] = 0x14
  data[2] = 0x00
  data[3] = 0x00
  data[4] = 0x00

  const state = await bluetoothSerialWrite(data)
  await bluetoothDisconnect()
  return state
}

export async function bluetoothLcd() {
  await bluetoothConnection()

  let iniLcd = new Uint8Array(5)
  iniLcd[0] = 0x01
  iniLcd[1] = 0x1A
  iniLcd[2] = 0x1C
  iniLcd[3] = 0x01
  iniLcd[4] = 0x00

  let test = new Uint8Array(5)
  test[0] = 0x1b
  test[1] = 0x1C
  test[2] = 0x1C
  test[3] = 0x04
  test[4] = 0x00
  // console.log('data =', data)

  // [1BH][51H][41H]d1d2d3…dn[0DH]
  // 31 32 33 34 35 36 0a

  // await bluetoothSerialWrite(iniLcd)
  const state = await bluetoothSerialWrite(test)
  await bluetoothDisconnect()
  return state
}