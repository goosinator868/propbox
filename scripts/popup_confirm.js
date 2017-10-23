function showConfirm(itemID) {
  console.log(itemID);
  var modal = null;
  modal = document.getElementById("confirm_"+itemID);
  console.log(modal)
  modal.style.display = "block";
  return;
}

function iShowConfirm(itemID,i) {
  console.log(itemID);
  var modal = null;
  modal = document.getElementById("confirm_"+i+"_"+itemID);
  console.log(modal)
  modal.style.display = "block";
  return;
}

function iCloseConfirm(itemID,i) {
  var modal = null;
  modal = document.getElementById("confirm_"+i+"_"+itemID);
  console.log(modal)
  modal.style.display = "none";
  return;
}

function closeConfirm(itemID) {
  var modal = null;
  modal = document.getElementById("confirm_"+itemID);
  console.log(modal)
  modal.style.display = "none";
  return;
}
