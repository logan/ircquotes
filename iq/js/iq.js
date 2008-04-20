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

function SignInForm() {
  this.form = $("signin_form");
  if (!this.form) {
    return;
  }

  this.ERROR_MESSAGES = {
    "NoSuchNameException": "Invalid account name",
    "InvalidPasswordException": "Invalid password",
    "NotActivatedException": "This account has not been activated",
  };

  this.button = $("signin_button");
  this.account = $("signin_account");
  this.password = $("signin_password");
  this.status = $("signin_status_message");
  this.throbber = new Throbber(32);

  this.account.onkeydown = bind(this.onKeyDown, this);
  this.password.onkeydown = bind(this.onKeyDown, this);
}

SignInForm.prototype.toggleEnabled = function() {
  this.account.disabled = !this.account.disabled;
  this.password.disabled = !this.password.disabled;
  this.button.disabled = !this.button.disabled;
  toggleElementClass("disabled", this.account);
  toggleElementClass("disabled", this.password);
  toggleElementClass("disabled", this.button);
  map(function(e) {
        e.style["background"] = this.button.style["background"];
      }, getElementsByTagAndClassName("*", "*", $("user_menu")));
};

SignInForm.prototype.handleResponse = function(response) {
  this.throbber.stop();
  if (response.success) {
    slideUp($("user_menu"), {"duration": 0.5});
    window.location.reload();
  } else {
    this.displayError(this.ERROR_MESSAGES[response.exception]);
  }
}

SignInForm.prototype.handleError = function(response) {
  this.throbber.stop();
  this.displayError("" + response);
}

SignInForm.prototype.displayError = function(msg) {
  this.toggleEnabled();
  this.status.innerHTML = msg;
}

SignInForm.prototype.maybeSubmit = function() {
  var controls = getElementsByTagAndClassName("input", "*", this.form);

  if (this.account.value.replace(/\s+/g, "").length == 0) {
    this.account.focus();
  } else if (this.password.value.length == 0) {
    this.password.focus();
  } else {
    this.toggleEnabled();
    this.throbber.start($("signin_throbber"));
    this.status.innerHTML = "Logging in...";

    var d_result = loadJSONDoc("/json/login",
                               {"name": this.account.value,
                                "password": this.password.value});

    d_result.addCallbacks(bind(this.handleResponse, this),
                          bind(this.handleError, this));
  }
}

SignInForm.prototype.onKeyDown = function(e) {
  var code;

  if (window.event) {
    code = window.event.keyCode;
  } else {
    code = e.which;
  }
  if (code == 13) {
    this.maybeSubmit();
  }
}

addLoadEvent(function() { new SignInForm(); });


function SignUpForm() {
  this.form = $("create_account_form");

  if (!this.form) {
    return;
  }

  this.button = $("create_account_button");
  this.name = $("create_account_name");
  this.email = $("create_account_email");
  this.password1 = $("create_account_password1");
  this.password2 = $("create_account_password2");

  this.button.disabled = true;
  this.button.onclick = bind(this.submit, this);

  this.name.onkeyup = bind(partial(this.maybeCheckField, "name"), this);
  this.checking_name = false;

  this.email.onkeyup = bind(partial(this.maybeCheckField, "email"), this);
  this.checking_email = false;

  this.password1.onkeyup = bind(this.check, this);
  this.password2.onkeyup = bind(this.check, this);

  roundElement("create_account", null);

  var node = getFirstElementByTagAndClassName("*", "step_by_step", "create_account");

  if (node) {
    roundElement(node, null);
  }

  this.name.focus();
}

SignUpForm.prototype.markError = function(field, msg) {
  var n = (field == null || field == "*")
          ? "create_account_msg"
          : "create_account_" + field + "_msg";

  removeElementClass($(n), "green");
  addElementClass($(n), "error");
  $(n).innerHTML = msg;
}

SignUpForm.prototype.clearError = function(field, msg) {
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

SignUpForm.prototype.maybeCheckField = function(field) {
  var node = this[field];

  if (!node.value) {
    return;
  }
  if (this["checking_" + field]) {
    this["pending_" + field] = true;
    return;
  }
  this["checking_deferred_" + field] = this.checkField(field);
  this["checking_" + field] = true;
  this["pending_" + field] = false;
}

SignUpForm.prototype.handleCheckFieldResponse = function(field, response) {
  var error = response[field + "_error"];

  if (error) {
    this.markError(field, error);
  } else {
    var msg = null;

    if (field == "name") {
      msg = "Available!";
    }
    this.clearError(field, msg);
  }
  this["checking_" + field] = false;
  if (this["pending_" + field]) {
    this.maybeCheckField(field);
  }
}

SignUpForm.prototype.checkField = function(field) {
  var node = this[field];
  var m = "create_account_" + field + "_msg";
  var params = {};

  params[field] = node.value;

  var d_result = loadJSONDoc("/json/create-account", params);

  this["checking_" + field] = d_result;
  d_result.addCallbacks(bind(partial(this.handleCheckFieldResponse, field),
                             this),
                        bind(this.handleError, this));
}

SignUpForm.prototype.handleError = function(error) {
  this.markError("*", error);
}

SignUpForm.prototype.validateName = function() {
  var name = this.name.value.replace(/^\s+/, "").replace(/\s+$/, "");
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
    this.markError("name", msg);
  }
  return false;
}

SignUpForm.prototype.validateEmail = function() {
  var email = this.email.value.replace(/^\s+/, "").replace(/\s+$/, "");

  if (email.length == 0) {
    return false;
  } else if (email.length > 32) {
    msg = "We only support email addresses up to 32 characters long.";
  } else if (!email.match(/^.+@.+\...+$/)) {
    msg = "This doesn't look like a valid email address.";
  } else {
    this.clearError("email", null);
    return true;
  }
  this.markError("email", msg);
  return false;
}

SignUpForm.prototype.validatePassword = function() {
  var password1 = this.password1.value;
  var password2 = this.password2.value;

  if (password1 != password2) {
    if (password2.length > 0) {
      this.markError("password", "Passwords do not match");
    } else {
      this.clearError("password", null);
    }
    return false;
  }
  this.clearError("password", null);
  return password1.length > 0;
}

SignUpForm.prototype.check = function() {
  var ok = true;

  ok &= this.validateName();
  ok &= this.validateEmail();
  ok &= this.validatePassword();
  this.button.disabled = !ok;
}

SignUpForm.prototype.handleSubmitResponse = function(response) {
  if (!response) {
    this.handleError("Server side error");
    return;
  }
  if (response.created) {
    this.handleSuccess(response.name, response.email,
                       response.activation,
                       response.confirmation);
  } else {
    if (response.name_error) {
      this.markError("name", response.name_error);
    }
    if (response.password_error) {
      this.markError("password", response.password_error);
    }
    this.markError("*", response.exception);
  }
}

SignUpForm.prototype.submit = function() {
  var params = {
    "create": "1",
    "name": this.name.value,
    "email": this.email.value,
    "password": this.password1.value
  };
  var d_response = loadJSONDoc("/json/create-account", params);

  d_response.addCallbacks(bind(this.handleSubmitResponse, this),
                          bind(this.handleError, this));
  d_response.addCallback(bind(this.check, this));
}

SignUpForm.prototype.handleSuccess =
    function(name, email, activation, confirmation) {
  var success = $("create_account_success");
  var link = $("create_account_activation_link");

  if (activation && link) {
    link.setAttribute("href", "/activate?name=" + encodeURI(name)
                      + (activation ? "&activation=" + activation : ""));
  }
  if (confirmation && $("create_account_activation_email")) {
    $("create_account_activation_email").innerHTML = "<pre>" + confirmation + "</pre>";
  }
  success.innerHTML = success.innerHTML.replace(/\$email/g, email);
  hideElement("create_account_form");
  showElement("create_account_success");
}

addLoadEvent(function() { new SignUpForm(); });

function Throbber(size) {
  this.size = size;
  this.delay = 1. / 32;
  this.frame = 1;
  this.stopped = true;
}

Throbber.prototype.start = function(container) {
  this.container = container;
  this.stopped = false;
  this.animateFrame();
}

Throbber.prototype.animateFrame = function() {
  if (this.stopped) {
    return;
  }

  if (this.frame == 0) {
    this.frame++;
  }

  var x = -this.size * (this.frame % 8);
  var y = -this.size * Math.floor(this.frame / 8);

  this.container.style.backgroundPosition = x + "px " + y + "px";
  this.frame = (this.frame + 1) % 32;
  callLater(this.delay, bind(this.animateFrame, this));
}

Throbber.prototype.stop = function() {
  this.container.style.backgroundPosition = "top left";
  this.stopped = true;
}
