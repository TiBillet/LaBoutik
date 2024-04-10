export default class socket {
  on (msg, data) {
    console.log('msg = ', msg)
    console.log( 'data = ', JSON.stringify(data, null, '\t'))
  }
  emit (msg, data) {
    console.log('msg = ', msg)
    console.log( 'data = ', JSON.stringify(data, null, '\t'))
  }
}