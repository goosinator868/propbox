/* Copyright (c) 2017 Future Gadget Laboratories.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

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
