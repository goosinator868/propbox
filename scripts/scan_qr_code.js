// Copyright (c) 2017 Future Gadget Laboratories.

// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:

// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.

// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

function scanQRCode(callback) {
  let scanner = new Instascan.Scanner({ video: document.getElementById('scanner_window'), mirror: false, backgroundScan: false });
  scanner.addListener('scan', function (content) {
    scanner.stop();
    $("#scanner_container").hide();
    callback(content);
  });
  // Close the scanner if someone clicks out of it.
  $("#scanner_container").click(function(){
    scanner.stop();
    $("#scanner_container").hide();
  });
  Instascan.Camera.getCameras().then(function (cameras) {
    if (cameras.length == 0) {
      // desktop
      scanner.start(cameras[0]);
    } else if (cameras.length > 0) {
      // mobile
      scanner.start(cameras[cameras.length - 1]);
    } else {
      console.error('No cameras found.');
      alert("No cameras found.");
    }
  }).catch(function (e) {
    console.error(e);
  });
}

function scanAndAddToList(list) {
  $("#scanner_container").show();
  scanQRCode(function(content){
    scanned_codes.push(content);
    new_content = document.createElement('li');
    new_content.textContent = content;
    document.getElementById('scanned_list').appendChild(new_content);
  });
}

function scanAndAddToList(list) {
      $("#scanner_container").show();
      scanQRCode(function(content){
        if (scanned_codes.indexOf(content) < 0) {
          scanned_codes.push(content);
          item = jQuery.getJSON("/item_from_qr_code?qr_code=" + content, "", function(item) {
              hidden_id = document.createElement('input');
              hidden_id.setAttribute("type", "hidden");
              hidden_id.setAttribute("name", "keys");
              hidden_id.setAttribute("value", item.urlsafe_key);
              document.getElementById('scanned_keys').appendChild(hidden_id);

              new_content = document.createElement('li');
              new_content.textContent = item.name;
              document.getElementById('scanned_list').appendChild(new_content);
            });
        }
      });
    }