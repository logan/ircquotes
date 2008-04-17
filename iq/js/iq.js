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
  map(function(elem) { roundElement(elem, {"corners": "tl tr"}); },
      getElementsByTagAndClassName("*", "roundtop"));
  map(function(elem) { roundElement(elem, {"corners": "bl br"}); },
      getElementsByTagAndClassName("*", "roundbottom"));
  map(function(elem) { roundElement(elem, null); },
      getElementsByTagAndClassName("*", "round"));
}
addLoadEvent(roundCorners);

function toggleMenu(id, control) {
  var menu = $(id + "_menu");

  toggleElementClass("active", control);
  if (getStyle(menu, "display") == "none") {
    slideDown(menu, {"duration": 0.5});
    if (id == "user") {
      var account = $("signin_account");

      if (account) {
        account.focus();
      }
    }
  } else {
    slideUp(menu, {"duration": 0.5});
  }
}

function setupMenu(id) {
  function setup() {
    toggleElementClass("menu", $(id + "_menu"));
    $(id + "_control").onclick = function() { toggleMenu(id, this); };
    roundElement($(id + "_menu"), {"corners": "bl br"});
  }
  addLoadEvent(setup);
}
setupMenu("browse");
setupMenu("user");

function toggleSignInFormEnabled() {
  $("signin_account").disabled = !$("signin_account");
  $("signin_password").disabled = !$("signin_password");
  toggleElementClass("disabled", $("signin_account"));
  toggleElementClass("disabled", $("signin_password"));
  toggleElementClass("disabled", $("signin_button"));
  map(function(e) {
        e.style["background"] = $("signin_button").style["background"];
      }, getElementsByTagAndClassName("*", "*", $("user_menu")));
};

function handleSignInResponse(response) {
  if (response.ok) {
    slideUp($("user_menu"), {"duration": 0.5});
    window.location.reload();
  } else {
    displaySignInError(response.reason);
  }
}

function handleSignInError(response) {
  displaySignInError("" + response);
}

function displaySignInError(msg) {
  toggleSignInFormEnabled();
  $("signin_status").innerHTML = msg;
}

function maybeSignIn() {
  var controls = getElementsByTagAndClassName("input", "*", $("signin_form"));
  var account = $("signin_account");
  var password = $("signin_password");

  if (account.value.replace(/\s+/g, "").length == 0) {
    account.focus();
  } else if (password.value.length == 0) {
    password.focus();
  } else {
    toggleSignInFormEnabled();
    $("signin_status").innerHTML = "Logging in ...";

    var d_result = loadJSONDoc("/login",
                               {"name": account.value,
                                "password": password.value});

    d_result.addCallbacks(handleSignInResponse, handleSignInError);
  }
}

function handleSignInKeyDown(e) {
  var code;

  if (window.event) {
    code = window.event.keyCode;
  } else {
    code = e.which;
  }
  if (code == 13) {
    maybeSignIn();
  }
}

function signOut() {
  slideUp($("user_menu"), {"duration": 0.5});
  window.location.href = "/logout";
}

function setupSigninForm() {
  function setup() {
    if ($("signin_button")) {
      $("signin_button").onclick = maybeSignIn;
      $("signin_account").onkeydown = handleSignInKeyDown;
      $("signin_password").onkeydown = handleSignInKeyDown;
    } else {
      $("signout_button").onclick = signOut;
    }
  }
  addLoadEvent(setup);
}
setupSigninForm();
