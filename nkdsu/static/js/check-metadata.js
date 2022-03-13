/* global jsmediatags */

(() => {
  const metadataForm = document.getElementById('check-metadata-form')
  metadataForm.style.display = 'none'

  const fileField = document.createElement('input')
  fileField.setAttribute('type', 'file')

  metadataForm.parentNode.insertBefore(fileField, metadataForm)

  fileField.addEventListener('change', e => {
    const file = fileField.files[0]
    console.log(jsmediatags.read(file, {
      onSuccess: tag => {
        metadataForm.querySelector('[name=id3_title]').value = tag.tags.title || ''
        metadataForm.querySelector('[name=id3_artist]').value = tag.tags.artist || ''
        metadataForm.querySelector('[name=composer]').value = tag.tags.TCOM.data || ''
        metadataForm.querySelector('[name=year]').value = tag.tags.year || tag.tags.TDRC.data || ''

        metadataForm.submit()
      },
      onError: error => {
        alert(`${error.type}: ${error.info}`)
      },
    }))
  })
})()
