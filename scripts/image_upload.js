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

PLACEHOLDER_IMAGE_SRC = "";


 $(function() {
  $('#add_item_form').submit(function() {
      $('#image_upload_input').prop('disabled', true);
      return true;
  });
  updatePreview();
});

MAX_WIDTH = 500;
MAX_HEIGHT = 500;
image_rotation_degrees = 0;

function onImageUpload() {
  image_rotation_degrees = 0;
  updatePreview();
}

function rotateCanvas(clockwise) {
    if (clockwise) {
        image_rotation_degrees += 90;
    } else {
        image_rotation_degrees -= 90;
    }
    updatePreview();
}

function drawImageToPreviewWindow(img, update_final_image) {
    height = img.height;
    width = img.width;
    scale = Math.min(MAX_HEIGHT/height, MAX_WIDTH/width);

    if (scale < 1) {
      height *= scale;
      width *= scale;
    }

    preview = document.getElementById('preview_canvas');
    if (Math.abs(image_rotation_degrees % 180) == 90) {
        preview.width = height;
        preview.height = width;
    } else {
        preview.width = width;
        preview.height = height;
    }
    var context = preview.getContext('2d');

    context.clearRect(0,0,preview.width,preview.height);
    context.save();
    context.translate(preview.width/2,preview.height/2);
    context.rotate(image_rotation_degrees * Math.PI / 180);
    context.drawImage(img,-width/2,-height/2, width, height);
    context.restore();
    if (update_final_image) {
      updateFinalImage();
    }
}

function updatePreview(e){
  // If there are no files uploaded.
  if (document.getElementById('image_upload_input').files.length == 0) {
    pre_existing_img = document.getElementById("item_image");
    // If there is an image that already exists (when we are editing an item)
    if (pre_existing_img) {
      var img = document.createElement('img');
      img.onload = function(){
        drawImageToPreviewWindow(img, true);
      };
      img.src = pre_existing_img.src;
    // If this is a brand new item or it does not have an image.
    } else {
      ctx = document.getElementById("preview_canvas").getContext('2d');
      ctx.font = "28px Arial";
      ctx.fillText("No image added",20,125);
      // placeholder_image = document.createElement('img');
      // placeholder_image.onload = function(){
      //   // Draw the placeholder, but don't update the actual image in the form.
      //   drawImageToPreviewWindow(placeholder_image, false);
      // };
      // img.src = PLACEHOLDER_IMAGE_SRC;
    }
  // If there are files uploaded.
  } else {
    // Get the file.
    input = document.getElementById('image_upload_input').files[0];
    r = new RegExp('/image.*/');
    // If the file is an image then load it into an <img> tag and then use it to draw on the canvas.
    if (!input.type.match(r)) {
      var img = document.createElement('img');
      img.onload = function(){
        drawImageToPreviewWindow(img, true);
      };
      img.src = window.URL.createObjectURL(input);
    };
  }
}

// Updates the downscaled image that will get uploaded with the form.
// The value is updated to the value on the preview canvas.
function updateFinalImage() {
  dataurl = document.getElementById('preview_canvas').toDataURL("image/png");
  data = dataurl.replace(/^data:image\/(png|jpg);base64,/, "");
  document.getElementById('downscaled_image').value = data;
}