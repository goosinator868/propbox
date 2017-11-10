function checkIn(key) {
    url = "/check_in?";
    url += "keys=" + key;
    $.ajax({
      type: "POST",
      dataType: "html",
      url: url ,
      data: "",
      success: function(data) {
        $("#item_" + key).find(".check_out_button").show();
        $("#item_" + key).find(".check_in_button").hide();
      },
    });
}

function showCheckOutPopup(key) {
    $("#item_" + key).find(".popup").show();
    $("#item_" + key).find(".check_out_button").hide();
}

function checkOut(key) {
    url = "/check_out";
    // url += "to_check_out=" + key;
    // url += '&reason=' + $("#item_" + key).find(".popup").find("reason").text();
    $.ajax({
      type: "POST",
      dataType: "html",
      url: url ,
      data: {'keys': key, 'reason': $("#item_" + key).find(".reason").val()},
      success: function(data) {
        $("#item_" + key).find(".check_out_button").hide();
        $("#item_" + key).find(".check_in_button").show();
        $("#item_" + key).find(".popup").hide();
      },
    });
}

function toggleListSignUp(key) {
  if ($("#item_" + key).find(".list_drop_down").is(":visible")) {
    hideListSignUp(key);
  } else {
    showListSignUp(key);
  }
}

function showListSignUp(key) {
  $("#item_" + key).find(".list_drop_down").show();
}

function hideListSignUp(key) {
  $("#item_" + key).find(".list_drop_down").hide();
}

function addToList(list_key, item_key) {
    url = "/add_to_list";
    $.ajax({
      type: "POST",
      dataType: "html",
      url: url ,
      data: {'list': list_key, 'item': item_key}});
}

function removeFromList(list_key, item_key) {
    url = "/remove_from_list";
    $.ajax({
      type: "POST",
      dataType: "html",
      url: url ,
      data: {'list': list_key, 'item': item_key}});
}

function toggleListMembership(checkbox, list_key, item_key) {
  if (checkbox.checked) {
    addToList(list_key, item_key);
  } else {
    removeFromList(list_key, item_key);
  }
}