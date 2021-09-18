function bindTrackGroupExpansionToggling() {
  const groupsContainer = document.querySelector(".track-groups")
  const toggleableTrackGroups = groupsContainer.querySelectorAll("details.track-group")
  if (toggleableTrackGroups.length === 0) {
    return
  }

  function setOpenStatus(open) {
    toggleableTrackGroups.forEach(function(detailsElement) {
      if (open) { detailsElement.setAttribute("open", true) }
      else { detailsElement.removeAttribute("open") }
    })
  }

  const buttonsParagraph = document.createElement("p")
  buttonsParagraph.classList.add("subheading")

  const collapseAllLink = document.createElement("a")
  collapseAllLink.append(new Text("collapse all"))
  collapseAllLink.addEventListener("click", function() { setOpenStatus(false) })
  buttonsParagraph.append(collapseAllLink)

  buttonsParagraph.append(new Text(" · "))

  const expandAllLink = document.createElement("a")
  expandAllLink.append(new Text("expand all"))
  expandAllLink.addEventListener("click", function() { setOpenStatus(true) })
  buttonsParagraph.append(expandAllLink)

  groupsContainer.before(buttonsParagraph)
}

$(document).ready(bindTrackGroupExpansionToggling);
