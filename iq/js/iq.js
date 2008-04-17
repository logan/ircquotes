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
    if (!$(id + "_menu")) {
      return;
    }
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

function setupSignInForm() {
  function setup() {
    if ($("signin_button")) {
      $("signin_button").onclick = maybeSignIn;
      $("signin_account").onkeydown = handleSignInKeyDown;
      $("signin_password").onkeydown = handleSignInKeyDown;
    } else if ($("signout_button")) {
      $("signout_button").onclick = signOut;
    }
  }
  addLoadEvent(setup);
}
setupSignInForm();


function markSignUpFormError(field, msg) {
  var n = (field == null || field == "*")
          ? "create_account_msg"
          : "create_account_" + field + "_msg";

  removeElementClass($(n), "green");
  addElementClass($(n), "error");
  $(n).innerHTML = msg;
}

function clearSignUpFormError(field, msg) {
  var n = (field == null || field == "*")
          ? "create_account_msg"
          : "create_account_" + field + "_msg";

  removeElementClass($(n), "error");
  $(n).innerHTML = "";
  if (msg) {
    addElementClass($(n), "green");
    $(n).innerHTML = msg;
  }
}

function maybeCheckSignUpField(field) {
  var node = $("create_account_" + field);

  if (node.checking) {
    node.pending = true;
    return;
  }
  node.checking_deferred = checkSignUpField(field);
  node.checking = true;
  node.pending = false;
}

function checkSignUpField(field) {
  var n = "create_account_" + field;
  var m = n + "_msg";
  var params = {};

  params[field] = $(n).value;

  var d_result = loadJSONDoc("/json/check-" + field, params);

  $(n).checking = d_result;
  d_result.addCallback(function(response) {
                         if (response.error) {
                           markSignUpFormError(field, response.reason);
                         } else {
                           clearSignUpFormError(field, null);
                         }
                       });
  d_result.addCallback(function() {
                         $(n).checking = false;
                         if ($(n).pending) {
                           maybeCheckSignUpField(field);
                         }
                       });
  d_result.addErrback(handleSignUpError);
}

function handleSignUpError(error) {
  markSignUpFormError("*", error);
}

function validateSignUpName() {
  var name = $("create_account_name").value
             .replace(/^\s+/, "").replace(/\s+$/, "");
  var msg;

  if (name.length == 0) {
    msg = "A name is required.";
  } else if (name.length > 20) {
    msg = "An account name may only be at most 20 characters in length.";
  } else if (!name.match(/\w/)) {
    msg = "An account name must contain at least one letter.";
  } else if (name.match(/[^\w\d'\[\]{}\\| -]/)) {
    msg = "An account name may only contain letters, numerals, apostrophes,"
          + " spaces, and other characters acceptable in IRC nicks.";
  } else {
    return true;
  }

  if (!hasElementClass($("create_account_name_msg"), "error")) {
    markSignUpFormError("name", msg);
  }
  return false;
}

function validateSignUpEmail() {
  var email = $("create_account_email").value
              .replace(/^\s+/, "").replace(/\s+$/, "");

  if (email.length == 0) {
    return false;
  } else if (email.length > 32) {
    msg = "We only support email addresses up to 32 characters long.";
  } else if (!email.match(/^.+@.+\...+$/)) {
    msg = "This doesn't look like a valid email address.";
  } else {
    clearSignUpFormError("email", null);
    return true;
  }
  markSignUpFormError("email", msg);
  return false;
}

function validateSignUpPassword() {
  var password1 = $("create_account_password1").value;
  var password2 = $("create_account_password2").value;

  if (password1 != password2) {
    if (password2.length > 0) {
      markSignUpFormError("password", "Passwords do not match");
    }
    return false;
  }
  return password1.length > 0;
}

function checkSignUpForm() {
  var ok = true;

  ok &= validateSignUpName();
  ok &= validateSignUpEmail();
  ok &= validateSignUpPassword();
  $("create_account_button").disabled = !ok;
}

function submitSignUpForm() {
  var params = {
    "name": $("create_account_name").value,
    "email": $("create_account_email").value,
    "password": $("create_account_password1").value
  };
  var d_response = loadJSONDoc("/json/create-account", params);

  d_response.addCallback(function(response) {
                           if (!response) {
                             handleSignUpError("Server side error");
                             return;
                           }
                           if (response.ok) {
                             handleSignUpSuccess(response.name, response.email,
                                                 response.activation,
                                                 response.confirmation);
                           } else {
                             if (response.errors) {
                               markSignUpFormError("name", response.errors.name);
                               markSignUpFormError("email", response.errors.email);
                               markSignUpFormError("password", response.errors.password);
                             }
                             markSignUpFormError("*", response.reason);
                           }
                         });
  d_response.addErrback(handleSignUpError);
  d_response.addCallback(checkSignUpForm);
}

function handleSignUpSuccess(name, email, activation, confirmation) {
  var success = $("create_account_success");
  var link = $("create_account_activation_link");

  link.setAttribute("href", "/activate?name=" + encodeURI(name)
                    + (activation ? "&activation=" + activation : ""));
  success.innerHTML = success.innerHTML.replace(/\$email/g, email);
  hideElement("create_account_form");
  showElement("create_account_success");
  if (confirmation) {
    document.writeln("<pre>" + confirmation + "</pre>");
  }
}

function installSignUpForm() {
  if (!$("create_account_form")) {
    return;
  }
  $("create_account_button").disabled = true;
  $("create_account_button").onclick = submitSignUpForm;
  $("create_account_name").checking = false;
  $("create_account_name").onkeyup =
      function() { maybeCheckSignUpField("name"); };
  $("create_account_email").onkeyup =
      function() { maybeCheckSignUpField("email"); };
  $("create_account_password1").onkeyup = checkSignUpForm;
  $("create_account_password2").onkeyup = checkSignUpForm;

  $("create_account_name").focus();

  roundElement("create_account", null);

  var node = getFirstElementByTagAndClassName("*", "step_by_step", "create_account");

  if (node) {
    roundElement(node, null);
  }
}
addLoadEvent(installSignUpForm);
