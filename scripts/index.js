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

function displayFilterCostumeForm() {
    document.getElementById("costume_specific_forms").style.display = 'block'
}

function hideFilterCostumeForm() {
    document.getElementById("costume_specific_forms").style.display = 'none'
}

function setCheckedRadioValues(radioListName, valueChecked) {
  var radioList = document.getElementsByName(radioListName);
  for (var i = 0; i < radioList.length; i++) {
        if (document.getElementById(radioList[i].id) != null) {
            document.getElementById(radioList[i].id).checked = false;
        }
  }
  if (document.getElementById(valueChecked) != null) {
      document.getElementById(valueChecked).checked = true;
  }
}

function setCheckboxValues(x) {
    if (typeof(Storage) !== "undefined") {
        var conditionArray = new Array();
        var articleArray = new Array();
        var costumeSizeStringArray = new Array();
        var costumeSizeNumArray = new Array();
        var colorArray = new Array();
        var tagGrouping = "tagGroupingInclusive";
        var colorGrouping = "colorGroupingInclusive";
        var itemType = "All";
        var itemAvailability = "availabilityAll";
        var nameText = document.getElementById("nameBox").value;
        var tagText = document.getElementById("tagBox").value;
        var conditionList = x.filter_by_condition;
        var articleList = x.filter_by_article;
        var costumeSizeStringList = x.filter_by_costume_size_string;
        var costumeSizeNumList = x.filter_by_costume_size_number;
        var itemTypeList = document.getElementsByName("filter_by_item_type");
        var itemColorList = x.filter_by_color;
        var itemAvailabilityList = document.getElementsByName("filter_by_availability");

        if (conditionList != null) {
            for (var i = 0; i < conditionList.length; i++) {
                if (conditionList[i].checked) {
                    conditionArray.push(conditionList[i].id);
                }
            }
        }

        if (articleList != null) {
            for (var i = 0; i < articleList.length; i++) {
                if (articleList[i].checked) {
                    articleArray.push(articleList[i].id);
                }
            }
        }

        costumeSizeString = $('#select_size_string').find(":selected").text();

        minSizeNum = document.getElementById("size-min").value;
        maxSizeNum = document.getElementById("size-max").value;
        excludeUnknownSize = document.getElementById("excludeUnknownSize").checked;

        if (document.getElementById("colorGroupingExclusive").checked) {
            colorGrouping = "colorGroupingExclusive";
        }

        if (document.getElementById("tagGroupingExclusive").checked) {
            tagGrouping = "tagGroupingExclusive";
        }

        if (itemTypeList != null) {
            for (var i = 0; i < itemTypeList.length; i++) {
                if (itemTypeList[i].checked) {
                    itemType = itemTypeList[i].id;
                }
            }
        }

        if (itemColorList != null) {
            for (var i = 0; i < itemColorList.length; i++) {
                if (itemColorList[i].checked) {
                    colorArray.push(itemColorList[i].id);
                }
            }
        }

        if (itemAvailabilityList != null) {
            for (var i = 0; i < itemAvailabilityList.length; i++) {
                if (itemAvailabilityList[i].checked) {
                    itemAvailability = itemAvailabilityList[i].id;
                }
            }
        }

        localStorage.setItem("ConditionFilter", JSON.stringify(conditionArray));
        localStorage.setItem("ArticleFilter", JSON.stringify(articleArray));
        localStorage.setItem("CostumeSizeStringFilter", costumeSizeString);
        localStorage.setItem("MinSizeNum", minSizeNum);
        localStorage.setItem("MaxSizeNum", maxSizeNum);
        localStorage.setItem("excludeUnknownSize", excludeUnknownSize);
        localStorage.setItem("ColorFilter", JSON.stringify(colorArray));
        localStorage.setItem("ColorGroupingFilter", colorGrouping);
        localStorage.setItem("TagGroupingFilter", tagGrouping);
        localStorage.setItem("ItemTypeFilter", itemType);
        localStorage.setItem("NameFilter", nameText);
        localStorage.setItem("TagFilter", tagText);
        localStorage.setItem("AvailabilityFilter", itemAvailability);
    }
}

function getCheckboxValues() {
    if (typeof(Storage) !== "undefined") {
        var conditionArray = JSON.parse(localStorage.getItem("ConditionFilter"));
        var articleArray = JSON.parse(localStorage.getItem("ArticleFilter"));

        var costumeSizeString = localStorage.getItem("CostumeSizeStringFilter");
        
        var minSizeNum = localStorage.getItem("MinSizeNum");
        var maxSizeNum = localStorage.getItem("MaxSizeNum");
        var excludeUnknownSize = localStorage.getItem("excludeUnknownSize");

        var colorArray = JSON.parse(localStorage.getItem("ColorFilter"));
        var colorGrouping = localStorage.getItem("ColorGroupingFilter");
        var tagGrouping = localStorage.getItem("TagGroupingFilter");
        var itemType = localStorage.getItem("ItemTypeFilter");
        var nameText = localStorage.getItem("NameFilter");
        var tagText = localStorage.getItem("TagFilter");
        var itemAvailability = localStorage.getItem("AvailabilityFilter");

        if (conditionArray == null) {
            conditionArray = [];
        }
        if (articleArray == null) {
            articleArray = [];
        }
        if (colorArray == null) {
            colorArray = [];
        }
        if (colorGrouping == null) {
            colorGrouping = "colorGroupingInclusive";
        }
        if (tagGrouping == null) {
            tagGrouping = "tagGroupingInclusive";
        }

        for (var i = 0; i < conditionArray.length; i++) {
            if (document.getElementById(conditionArray[i]) != null) {
                document.getElementById(conditionArray[i]).checked = true;
            }
        }

        for (var i = 0; i < articleArray.length; i++) {
            if (document.getElementById(articleArray[i]) != null) {
                document.getElementById(articleArray[i]).checked = true;
            }
        }

        $('#select_size_string').val(costumeSizeString);
        document.getElementById("excludeUnknownSize").checked = excludeUnknownSize == "true";
        document.getElementById("size-min").value = minSizeNum;
        document.getElementById("size-max").value = maxSizeNum;

        for (var i = 0; i < colorArray.length; i++) {
            if (document.getElementById(colorArray[i]) != null) {
                document.getElementById(colorArray[i]).checked = true;
            }
        }

        if (colorGrouping != null) {
            document.getElementById(colorGrouping).checked = true;
        } else {
            document.getElementById("colorGroupingInclusive").checked = true;
        }

        if (tagGrouping != null) {
            document.getElementById(tagGrouping).checked = true;
        } else {
            document.getElementById("tagGroupingInclusive").checked = true;
        }

        if (itemType != null) {
            document.getElementById(itemType).checked = true;
        } else {
            document.getElementById("typeAll").checked = true;
        }

        if (itemAvailability != null) {
            document.getElementById(itemAvailability).checked = true;
        } else {
            document.getElementById("availabilityAll").checked = true;
        }

        document.getElementById("nameBox").value = nameText;
        document.getElementById("tagBox").value = tagText;

        if (itemType == "typeCostume") {
            displayFilterCostumeForm();
        }
    }
}

function clearForm() {
  localStorage.setItem("ConditionFilter", JSON.stringify([]));
  localStorage.setItem("ArticleFilter", JSON.stringify([]));
  localStorage.setItem("CostumeSizeStringFilter", 'N/A');
  localStorage.setItem("MinSizeNum", "0");
  localStorage.setItem("MaxSizeNum", "26");
  localStorage.setItem("excludeUnknownSize", "False");
  localStorage.setItem("ColorFilter", JSON.stringify([]));
  localStorage.setItem("ColorGroupingFilter", "colorGroupingInclusive");
  localStorage.setItem("TagGroupingFilter", "tagGroupingInclusive");
  localStorage.setItem("ItemTypeFilter", "typeAll");
  localStorage.setItem("NameFilter", "");
  localStorage.setItem("TagFilter", "");
  localStorage.setItem("AvailabilityFilter", "availabilityAll");
  getCheckboxValues();
}
