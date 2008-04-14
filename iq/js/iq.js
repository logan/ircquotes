function roundNavTitleCorners(nav) {
  var options = {
    "corners": "bl br"
  };
  roundElement(nav, options);

  var titles = getElementsByTagAndClassName("h1", null, nav);

  if (titles.length > 0) {
    options = {
      "corners": "tl tr"
    };

    roundElement(titles[0], options);
  }
}

function roundCorners() {
  map(roundNavTitleCorners, getElementsByTagAndClassName("*", "nav"));
  map(function(elem) { roundElement(elem, {"corners": "tl tr"}); },
      getElementsByTagAndClassName("*", "roundtop"));
  map(function(elem) { roundElement(elem, {"corners": "bl br"}); },
      getElementsByTagAndClassName("*", "roundbottom"));
  roundElement($("content_container"), null);
}
addLoadEvent(roundCorners);
