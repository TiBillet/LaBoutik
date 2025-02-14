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

// --- bluetooth ---
export async function bluetoothGetMacAddress(name) {
  let retour = 'unknown'
  const list = await new Promise((resolve) => {
    // list devices
    bluetoothSerial.list(function (devices) {
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
  return retour
}

/**
 * async bluetooth is connected
 */
async function bluetoothIsConnected() {
  const test = await new Promise((resolve) => {
    bluetoothSerial.isConnected(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
    })
  })
  return test
}

/**
 * async bluetooth connect
 * @param {string} macAddress
 * @returns
 */
async function bluetoothConnect(macAddress) {
  const test = await new Promise((resolve) => {
    bluetoothSerial.connect(macAddress, async (result) => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothConnect, error = ${error}`)
    })
  })
  return test
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

async function bluetoothSerialWrite(contentToWrite) {
  const write = await new Promise((resolve) => {
    bluetoothSerial.write(contentToWrite, () => {
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
    bluetoothSerial.disconnect(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothDisconnect, error = ${error}`)
    })
  })
  return disconnect
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
