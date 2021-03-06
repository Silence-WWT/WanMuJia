// 整体组件
var AddressList = React.createClass({displayName: "AddressList",
    getInitialState: function() {
        return {
            nowAddress: null,
            isWrapShow: false
        };
    },
    handleBtnClick: function() {
        this.setState({isWrapShow: !this.state.isWrapShow});
    },
    handleSelectAddress: function(selectCt) {
        this.setState({nowAddress: selectCt,isWrapShow: false});
        if(this.props.setCity) {
            this.props.setCity(selectCt);
        }
    },
    render: function() {
        return (
            React.createElement("div", {className: "AddressList"}, 
                React.createElement(AddressDropButton, {triangleState: this.state.isWrapShow, onClick: this.handleBtnClick}, 
                    this.state.nowAddress?this.state.nowAddress:this.props.localAddress
                ), 
                this.state.isWrapShow?
                    React.createElement(AddressWrap, {addressData: this.props.addressData, localAddress: this.props.localAddress, handleSelectAddress: this.handleSelectAddress})
                    :null
                
            )
        );
    }
});

// 下拉按钮
var AddressDropButton = React.createClass({displayName: "AddressDropButton",
    handleClick: function() {
        this.props.onClick();
    },
    render: function() {
        return (
            React.createElement("button", {className: "AddressDropButton", onClick: this.handleClick}, 
                this.props.children, 
                React.createElement("span", {className: "triangle "+this.props.triangleState})
            )
        );
    }
});

// 地址操作框容器
var AddressWrap = React.createClass({displayName: "AddressWrap",
    render: function() {
        return (
            React.createElement("div", {className: "AddressWrap"}, 
                React.createElement("div", {className: "AddressCont"}, 
                    React.createElement(AddressLocation, {localAddress: this.props.localAddress, handleSelectAddress: this.props.handleSelectAddress}), 
                    React.createElement(AddressSearchInput, {addressData: this.props.addressData, handleSelectAddress: this.props.handleSelectAddress}), 
                    React.createElement(AddressListWrap, {addressData: this.props.addressData, handleSelectAddress: this.props.handleSelectAddress})
                )
            )
        );
    }
});

// 定位当前地址
var AddressLocation = React.createClass({displayName: "AddressLocation",
    handleClick: function() {
        this.props.handleSelectAddress(this.props.localAddress);
    },
    render: function() {
        return (
            React.createElement("div", {className: "AddressLocation"}, 
                "猜你在：", React.createElement("span", {onClick: this.handleClick}, this.props.localAddress)
            )
        );
    }
});

// 地址搜索
var AddressSearchInput = React.createClass({displayName: "AddressSearchInput",
    getInitialState: function() {
        return {
            result: [],
        };
    },
    handleResultClick: function(e) {
        var address = e.target.getAttribute('data');
        this.props.handleSelectAddress(address);
    },
    handleSearch: function(event) {
        var cont = event.target.value;
        var len = cont.length;
        var addressData = this.props.addressData;
        // 判断是汉字还是拼音
        var reg=/^[\u4E00-\u9FA5]+$/;
        if(reg.test(cont)) {
            // 是汉字处理
            var _resultH = [];
            var j = 0;
            for(var keyH in addressData) {
                for(var keyHS in addressData[keyH]) {
                    if(addressData[keyH][keyHS].city.substring(0,len) == cont) {
                        _resultH[j]  = addressData[keyH][keyHS].city;
                        j++;
                    }
                }
            }
            this.setState({result: _resultH});
            return ;
        }
        // 是拼音
        var FL = cont.substring(0,1).toLocaleUpperCase();
        var resultFL = addressData[FL];
        var _result = [];
        var i = 0;
        for(var key in resultFL) {
            if(key.substring(0,len) == cont.toLocaleLowerCase()) {
                _result[i]  = resultFL[key].city;
            }
            i++;
        }
        this.setState({result: _result});
    },
    render: function() {
        var _handleResultClick = this.handleResultClick;
        var resultNodes = this.state.result.map(function (result) {
            return (
                React.createElement("li", {data: result, onClick: _handleResultClick}, result)
            );
        });
        return (
            React.createElement("div", {className: "AddressSearch"}, 
                "直接搜索", 
                React.createElement("input", {onChange: this.handleSearch, placeholder: "请输入城市名"}), 
                React.createElement("ul", {className: "AddressSearchResult"}, 
                    resultNodes
                )
            )
        );
    }
});

// 地址列表容器
var AddressListWrap = React.createClass({displayName: "AddressListWrap",
    render: function() {
        var addressData = this.props.addressData;
        var handleSelectAddress = this.props.handleSelectAddress;
        var rowNodes = function(data) {
            var cont = [];
            var i = 0;
            for(var key in data) {
                cont[i]  = React.createElement(AddressListRow, {key: key, keyData: key, data: data[key], handleSelectAddress: handleSelectAddress});
                i++;
            }
            return cont;
        }(addressData);
        return (
            React.createElement("div", {className: "AddressListWrap"}, 
                rowNodes
            )
        );
    }
});

// 地址列表行
var AddressListRow = React.createClass({displayName: "AddressListRow",
    handleClick: function(e) {
        var address = e.target.getAttribute('data');
        this.props.handleSelectAddress(address);
    },
    render: function() {
        var handleClick = this.handleClick;
        var dataNodes = function(data) {
            var cont = [];
            var i = 0;
            for(var key in data) {
                cont[i]  = React.createElement("span", {key: "p"+key}, React.createElement("span", {data: data[key].city, key: i, onClick: handleClick}, data[key].city));
                i++;
            }
            return cont;
        }(this.props.data);
        return (
            React.createElement("div", {className: "AddressListRow"}, 
                React.createElement("span", {className: "keyData"}, this.props.keyData), 
                React.createElement("span", {className: "dataWrap"}, dataNodes)
            )
        );
    }
});

'use strict'

//  ==================================================
//  Include: AddressList AddressSearch
//
//  TODO:
//  ==================================================

var AddressPicker = React.createClass({displayName: "AddressPicker",
  getInitialState: function() {
    return {
      city: "北京",
      currentCity: null,
      address: this.props.keyword
    };
  },
  getDefaultProps: function() {
    return {};
  },
  componentWillMount: function() {
    var myCity = new BMap.LocalCity();
    myCity
      .get(function(res) {
        var currentCity = res.name;
        this.setState({
            currentCity: currentCity,
            city: currentCity
        });
      }.bind(this));
  },
  setAddress: function(ad) {
    this.setState({
      address: ad
    });
  },
  setCity: function(ct) {
    this.setState({
      city: ct
    });
  },
  render: function() {
    var addressPickerActiveStyle = this.state.address
      ? this.props.addressPickerActiveStyle
      : {};
    return (
      React.createElement("div", {className: "address-picker", style: addressPickerActiveStyle}, 
        React.createElement(AddressList, {setCity: this.setCity, localAddress: this.state.currentCity, addressData: this.props.addressData}), 
        React.createElement(AddressInput, React.__spread({},  this.props, {city: this.state.city, searchSubmitHandler: this.setAddress})), 
        React.createElement(AddressMap, {addressKeyword: this.state.address, city: this.state.city, theme: this.props.theme, lbs: this.props.lbs})
      )
    );
  }
});

'use strict'

//  ==================================================
//  Include: AddressInput AddressMap
//
//  TODO: [add] 增加各项参数
//  ==================================================

/* AddressSearch */
var AddressSearch = React.createClass({displayName: "AddressSearch",
  getInitialState: function() {
    return {
      address: null
    };
  },
  getDefaultProps: function() {
    return {
      inputWidth: 400,
      inputTip: "输入想要搜索的地址",
      searchBtnText: "搜索",
      city: "北京",
      theme: "dark"
    }
  },
  componentWillMount: function() {
    var myCity = new BMap.LocalCity();
    myCity
      .get(function(res) {
        var currentCity = res.name;
        this.setCity(currentCity);
      }.bind(this));
  },
  setAddress: function(ad) {
    this.setState({
      address: ad
    });
  },
  setCity: function(ct) {
    this.setState({
      city: ct
    });
  },
  render: function() {
    return (
      React.createElement("div", {className: "address-search"}, 
        React.createElement(AddressInput, React.__spread({},  this.props, {searchSubmitHandler: this.setAddress})), 
        React.createElement(AddressMap, {addressKeyword: this.state.address, city: this.props.city, theme: this.props.theme})
      )
    );
  }
});

/* AddressInput */
var AddressInput = React.createClass({displayName: "AddressInput",
  getInitialState: function() {
    return {
      keyword: this.props.keyword
    };
  },
  getDefaultProps: function() {
    return {
      inputWidth: 400,
      inputTip: "输入想要搜索的地址",
      searchBtnText: "搜索",
      city: "北京",
      theme: "light"
    }
  },
  searchSubmit: function() {
    var keyword = this.getDOMNode()
      .children[0]
      .value;
    var date = new Date();
    this.props
      .searchSubmitHandler(keyword);
    setCookie('searchKeyword', keyword, date.setDate(date.getDate() + 30));
  },
  checkEnter: function(e) {
    (e.keyCode === 13) && this.searchSubmit();
  },
  componentDidMount: function() {
    var mapAutoComplete = new BMap.Autocomplete({
      "input": "_addressSearchKeyword",
      "location": this.props.city
    });
  },
  render: function() {
    var keywordStyle = {
      width: this.props.inputWidth
    };
    var conClassName = "address-input";
    switch (this.props.theme) {
    case 'light' :
      break;
    case 'dark' :
      conClassName += " dark";
      break;
    default :

    }
    return (
      React.createElement("div", {className: conClassName}, 
        React.createElement("input", {className: "input-keyword", id: "_addressSearchKeyword", onKeyUp: this.checkEnter, placeholder: this.state.keyword || this.props.inputTip, style: keywordStyle}), 
        React.createElement("button", {className: "input-commit", onClick: this.searchSubmit}, this.props.searchBtnText)
      )
    );
  }
});

/* AddressMap */
var AddressMap = React.createClass({displayName: "AddressMap",
  getInitialState: function() {
    return {
      mapLocalObj: null,
      itemsNumber: 0,
      itemsList: [],
      itemActive: 0
    };
  },
  getDefaultProps: function() {
    return {
      theme: "light"
    }
  },
  componentDidMount: function() {
    this.map = new BMap.Map("_addressMapMain", {
      enableMapClick: false
    });
    this.map
      .centerAndZoom(this.props.city, 12);
  },
  componentWillReceiveProps: function(nextProps) {
    nextProps.addressKeyword && this.getNearby(nextProps.addressKeyword);
  },
  getNearby: function(keyword, page) {
    // 地址解析获取经纬度
    var myGeo = new BMap.Geocoder();
    var _this = this;
    myGeo
      .getPoint(keyword, function(point) { // 解析成功后的回调 搜索信息
        if (point) {
          myGeo.getLocation(point, function(geo) {
            if(_this.compareCity(geo.addressComponents.city, _this.props.city)) {
              $.ajax({
                type: 'get',
                url: 'http://api.map.baidu.com/geosearch/v3/nearby',
                dataType: "jsonp",
                data: {
                  ak: _this.props.lbs.ak,
                  geotable_id: _this.props.lbs.geotableId,
                  location: point.lng + ',' + point.lat,
                  radius: _this.props.lbs.radius,
                  tags: _this.props.lbs.tags,
                  sortby: _this.props.lbs.sortby,
                  page_index: _this.props.lbs.page || 0,
                  filter: _this.props.lbs.filter,
                  page_size: 50
                },
                jsonp: 'callback',
                success: function(res) {
                  _this.setState({
                    itemsNumber: res.total,
                    itemsList: res.contents
                  });
                  _this.showNearby();
                  _this.map
                    .centerAndZoom(_this.props.addressKeyword, 12);
                }
              })
            } else {
              _this.noItemsToShow();
            }
          });
        } else {
          _this.noItemsToShow();
        }
      }.bind(this), this.props.city);
  },
  compareCity: function(ct1, ct2) {
    return ct1.replace(/市$/,'') === ct2.replace(/市$/,'');
  },
  noItemsToShow: function() {
    console.log('暂无商家');
  },
  showNearby: function() {
    var _this = this;
    for (var k in this.state.itemsList) {
      var point = new BMap.Point(this.state.itemsList[k].location[0], this.state.itemsList[k].location[1]);
      var marker = new BMap.Marker(point);
      var label = new BMap.Label(String.fromCharCode(65 + parseInt(k)), {
        offset: new BMap.Size(4, 2)
      });
      label.setStyle({
        border: 'none',
        backgroundColor: 'transparent',
        color: '#FAFAFA'
      });
      marker.setLabel(label);
      marker.setTitle(this.state.itemsList[k].title);
      marker
        .addEventListener('click', function(e) {
          _this.showInfoWindow(this.getLabel().content.charCodeAt(0) - 65);
        });
      this.map
        .addOverlay(marker);
    }
    this.state.itemsList.length && this.showInfoWindow(0);
  },
  showInfoWindow: function(index) {
    if (index !== this.state.itemActive || 1) {
      var point = new BMap.Point(this.state.itemsList[index].location[0], this.state.itemsList[index].location[1]);
      var itemInfo = this.state.itemsList[index];
      var title = itemInfo.title;
      var address = itemInfo.address;
      var tel = itemInfo.tel;
      var content = '<p class="map-info-window">地址：' + address + '</p>';
      var infoWindow = new BMap.InfoWindow(content, {
        title: title,
        width: 290,
        panel: "panel",
        enableAutoPan: true,
        offset: new BMap.Size(0, -25)
      });
      this.setState({
        itemActive: + index
      });
      this.map
        .openInfoWindow(infoWindow, point);
    }
  },
  clickMapItem: function(e) {
    var ele = e.target;
    var eleClass = ele.getAttribute('class');
    var itemIndex = 0;
    if (eleClass === "map-item") {
      itemIndex = ele.getAttribute('data-key');
    } else if (eleClass === "map-item-mark" || eleClass === "map-item-main") {
      itemIndex = ele.parentNode
        .getAttribute('data-key');
    } else if (!eleClass) {
      itemIndex = ele.parentNode
        .parentNode
        .parentNode
        .getAttribute('data-key');
    } else {
      itemIndex = ele.parentNode
        .parentNode
        .getAttribute('data-key');
    }
    this.showInfoWindow(itemIndex);
  },
  render: function() {
    var conClassName = "address-map";
    switch (this.props.theme) {
    case 'light' :
      break;
    case 'dark' :
      conClassName += " dark";
      break;
    default :

    }
    var mapItemActieStyle = {
      backgroundColor: "#181211"
    };
    return (
      React.createElement("div", {className: conClassName, style: {
        display: this.props.addressKeyword
          ? "block"
          : "none"
      }}, 
        React.createElement("div", {className: "map-nav"}, 
          React.createElement("div", {className: "map-nav-title"}, 
            "附近有", 
            React.createElement("span", {className: "map-nav-number"}, 
              this.state.itemsNumber
            ), 
            "家体验店"
          ), 
          React.createElement("ul", {className: "map-items", id: "_addressMapItems", onClick: this.clickMapItem}, 
            this.state.itemsList.length ?
              this.state.itemsList.map(function (item, i) {
                return React.createElement("li", {className: "map-item", "data-key": i, key: i, style: (i === this.state.itemActive)
                  ? mapItemActieStyle
                  :
                    {}}, 
                  React.createElement("span", {className: "map-item-mark"}, String.fromCharCode(65 + i)), 
                  React.createElement("div", {className: "map-item-main"}, 
                    React.createElement("div", {className: "map-item-title"}, item.title), 
                    React.createElement("div", {className: "map-item-address"}, "地址：", item.address), 
                    React.createElement("div", {className: "map-item-tel"}, "电话：", item.tel)
                  )
                );
              }.bind(this)) :
              React.createElement("div", {className: "no-items"}, "您所在的城市目前还没有该家具的体验馆，敬请期待")
            
          )
        ), 
        React.createElement("div", {className: "map-main", id: "_addressMapMain"})
      )
    );
  }
});


//  ==================================================
//  Component: FilterGroup
//
//  Include: Filter FilterOption FilterAction FilterStateBar FilterStateTag
//
//  TODO:
//  ==================================================

/* 每条过滤器的每个选项 */
var FilterOption = React.createClass({displayName: "FilterOption",
  render: function () {
    var optionValue = this.props.value;
    // var select = this.props.onSelect.bind(null, optionValue);
    var select = function (event) {
      !this.props.isMultiSelect && event && event.preventDefault();
      this.props.onSelect(optionValue);
    }.bind(this);
    var optionElement;
    var optionValueElement = React.createElement("span", null, optionValue.value);
    if (this.props.isMultiSelect) {
      optionElement = (
        React.createElement("label", {href: "#", htmlFor: optionValue.name}, 
          React.createElement("input", {onClick: select, type: "checkbox", name: optionValue.name, value: optionValue.value, id: optionValue.value}), 
          optionValueElement
        )
      );
    }
    else {
      optionElement = (
        React.createElement("a", {href: "#", onClick: select}, 
          optionValueElement
        )
      );
    }
    return optionElement;
  }
});

/* 每条过滤器的额外操作 */
var FilterAction = React.createClass({displayName: "FilterAction",
  render: function () {
    return (
      React.createElement("div", {className: "filter-action"}, 
        React.createElement("a", {style: {display: this.props.multiToggleStatus ? 'inline' : 'none'}, 
          onClick: this.props.multiToggle, href: "#", className: "multi-toggle"}, "多选"), 
        React.createElement("a", {onClick: this.props.expandToggle, href: "#"}, 
          this.props.expandToggleStatus ? '更多' : '收起'
        )
      )
    );
  }
});

/* 状态标签 */
var FilterStateTag = React.createClass({displayName: "FilterStateTag",
  render: function () {
    var tagValueNodes;
    var removeTag = function (value, event) {
      event && event.preventDefault();
      this.props.onTagRemove(value);
    }.bind(this);
    var currStateValues =  Array.isArray(this.props.value) ?
                          this.props.value :
                          [this.props.value];
    tagValueNodes = currStateValues.map(function (value, index, values) {
      if (this.props.treeView) {
        // state 为 treeView
        return (
          React.createElement("span", {key: index}, 
            value.value, " ", 
            React.createElement("span", {className: "tag-remove"}, 
              React.createElement("a", {onClick: removeTag.bind(this, value), href: "#"}, "×")
            ), 
            
              index == values.length - 1 ?
                null :
                (React.createElement("span", null, ">"))
            
          )
        );
      }
      // state 不是 treeView 但可能为多选状态
      if (index == values.length - 1) {
        return (
          React.createElement("span", {key: index}, 
            value.value, " ", 
            React.createElement("span", {className: "tag-remove"}, 
              React.createElement("a", {onClick: removeTag.bind(this, value), href: "#"}, "×")
            )
          )
        );
      }
      else {
        return (
          React.createElement("span", {key: index}, 
            value.value + ',', " "
          )
        );
      }
    }.bind(this));

    return (
      React.createElement("div", {className: "filter-tag"}, 
        React.createElement("div", {className: "tag-name"}, this.props.name + ':', " "), 
        React.createElement("div", {className: "tag-value"}, 
          tagValueNodes
        )
      )
    );
  }
});

/* 状态标签栏 */
var FilterStateBar = React.createClass({displayName: "FilterStateBar",
  render: function () {
    var filterState = this.props.filterState;
    var stateTagNodes = Object.keys(filterState)
      .map(function (field, index) {
        var state = filterState[field];
        var def = this.props.getFilterDef(field);
        return (
          React.createElement(FilterStateTag, {
            key: index, 
            name: def.name, 
            value: state, 
            treeView: def.treeView, 
            onTagRemove: this.props.onStateDelete.bind(null, field)}
          )
        );
      }.bind(this));
    return (
      React.createElement("div", {className: "filter-state"}, 
        React.createElement("div", {className: "custom-content"}, 
          this.props.children
        ), 
        React.createElement("div", {className: "filter-tags"}, 
          stateTagNodes
        )
      )
    );
  }
});

/* 单条过滤器 */
var Filter = React.createClass({displayName: "Filter",
  getInitialState: function () {
    return {
      isMultiSelect: false,
      isExpanded: false,
      multiSelected: {}    // 暂时被多选中的选项
    };
  },
  getDefaultProps: function () {
    return {
      canMultiSelect: false,
      treeView: false,
      options: [],
    };
  },
  multiSelectToggle: function (event) {
    event && event.preventDefault();
    this.setState({
      isMultiSelect: !this.state.isMultiSelect,
      // 若由非多选到多选，则自动展开
      isExpanded: this.state.isMultiSelect ? false : true
    });
  },
  expandToggle: function (event) {
    event && event.preventDefault();
    this.setState({
      // 若由展开到收起，则取消多选状态
      isMultiSelect: this.state.isExpanded ? false : this.state.isMultiSelect,
      isExpanded: !this.state.isExpanded
    });
  },
  // 用于更新暂时被多选中的选项状态
  updateMultiSelected: function (value) {
    var multiSelected = this.state.multiSelected;
    multiSelected[value.value] ?
      multiSelected[value.value] = null :
      multiSelected[value.value] = value;
    this.setState({multiSelected: multiSelected});
  },
  // 确认多选的状态
  confirmMultiSelect: function (event) {
    event && event.preventDefault();
    var selectedObj = this.state.multiSelected;
    var selectedArr = [];
    for (var key in selectedObj) {
      if (selectedObj.hasOwnProperty(key) && selectedObj[key]) {
        selectedArr.push(selectedObj[key]);
      }
    }
    this.props.onSelectOption(selectedArr);
    // 清空多选暂存
    this.setState({multiSelected: {}});
    // 取消多选状态
    this.multiSelectToggle();
  },
  render: function () {
    var handleSelect = function (value) {
      if (!this.state.isMultiSelect) {
        this.props.onSelectOption(value);
        return;
      }
      this.updateMultiSelected(value);
    }.bind(this);
    var optionNodes = this.props.options.map(function (option, index) {
      return (
        React.createElement("li", {key: index, className: "filter-item"}, 
          React.createElement(FilterOption, {value: option, onSelect: handleSelect, isMultiSelect: this.state.isMultiSelect})
        )
      );
    }.bind(this));

    return (
      React.createElement("div", {className: "filter" + (this.state.isExpanded ? " expanded" : ""), style: {display: this.props.options.length > 0 ? 'block' : 'none'}}, 
        React.createElement("div", {className: "head"}, 
          React.createElement("h4", {className: "filter-name"}, this.props.name)
        ), 

        React.createElement("div", {className: "body"}, 
          React.createElement("ul", {className: "filter-items"}, 
            optionNodes
          ), 

          React.createElement("div", {style: {display: this.state.isMultiSelect ? 'block' : 'none'}, 
              className: "multi-confirm"}, 
            React.createElement("button", {className: "btn-confirm", onClick: this.confirmMultiSelect, type: "button", name: "confirm"}, "确定"), 
            React.createElement("button", {className: "btn-cancel", type: "button", name: "cancel", onClick: this.multiSelectToggle}, "取消")
          )
        ), 

        React.createElement("div", {className: "foot"}, 
          React.createElement(FilterAction, {
            multiToggleStatus: this.props.canMultiSelect &&
              !this.state.isMultiSelect, 
            expandToggleStatus: !this.state.isExpanded, 
            multiToggle: this.multiSelectToggle, 
            expandToggle: this.expandToggle}
          )
        )
      )
    );
  }
});

/* 过滤器组，最外层组件 */
/**
 * [props]
 * {object} filterDefs
 * {object} filterValues
 * {function} onStateChange
 */
var FilterGroup = React.createClass({displayName: "FilterGroup",
  getInitialState: function () {
    return {
      filterValues: this.props.filterValues,
      filterState: {}
    };
  },
  getDefaultProps: function () {
    return {
      filterValues: {},
      onStateChange: function () {}
    };
  },
  componentDidMount: function () {
    var defs = this.props.filterDefs
      .reduce(function (defs, filterDef) {
        defs[filterDef.field] = filterDef;
        return defs;
      }, {});
    this.setState({defIndex: defs});
  },
  updateFilterValue: function (values) {
    this.setState({filterValues: values});
  },
  setFilterState: function (state) {
    // if (!this.isSameState(this.state.filterState, state)) {
    this.setState({filterState: state});
    // }
  },
  addFilterState: function (field, value) {
    var that = this;
    var defs = that.state.defIndex;
    var state = this.state.filterState;
    var changed = false;
    var hasValue = !!state[field];

    if (defs[field].treeView) {
      var indexOfTree = hasValue ?
        that.findIndex(state[field], value) :
        -1;
      // 判断当前点击的和上一个选项是否是同一个层级
      var isSameLevel = function () {
        if (!hasValue) {
          return false;
        }
        var len = state[field].length;
        var currentState = that.props.filterValues[field] || [];
        return that.findIndex(currentState, value) > -1 &&
          that.findIndex(currentState, state[field][len - 1]) > -1;
      };
      // 当一开始没有值或点击的不是最后一个层级时，标记状态为改变
      changed = !hasValue || (indexOfTree != state[field].length - 1);
      if (changed) {
        state[field] = state[field] || [];
        // 如果已有此层级的选项，直接定位到此层级
        if (indexOfTree >= 0) {
          state[field] = state[field].slice(0, indexOfTree + 1);
        }
        else {
          // 当下一层级的选项还未加载时可能对同一层级的选项做多次选择
          // 此时保持同一层级选择的互斥性，总是只能选择一个选项
          if (isSameLevel()) {
            state[field].pop();
          }
          state[field].push(value);
        }
      }
    }
    // 非 treeView
    // 无该 field 下的 state，或 value 值不相等，或 value 数组不相等
    else if (!hasValue ||
      value.value !== state[field].value ||
      (Array.isArray(value) && !that.isSameState(value, state[field]))
    ) {

      if (Array.isArray(value) && value.length === 0) {
        that.removeFilterState(field);
      }
      else {
        state[field] = value;
        changed = true;
      }
    }

    // fire
    if (changed) {
      that.setState({filterState: state});
      that.props.onStateChange(this.state.filterState, that);
    }
  },
  removeFilterState: function (field, value) {
    var defs = this.state.defIndex;
    var state = this.state.filterState;
    var indexOfTree;
    if (defs[field].treeView) {
      indexOfTree = this.findIndex(state[field], value);
      if (indexOfTree === 0) {
        delete state[field];
      }
      else if (indexOfTree > 0) {
        state[field] = state[field].slice(0, indexOfTree);
      }
    }
    else {
      delete state[field];
    }

    // fire
    this.setState({filterState: state});
    this.props.onStateChange(this.state.filterState, this);
  },
  getFilterDef: function (field) {
    return this.state.defIndex[field];
  },

  // util fn
  isSameState: function (o, n) {
    var that = this;
    if (that.isEmptyObj(o) && !that.isEmptyObj(n) ||
      !that.isEmptyObj(o) && that.isEmptyObj(n)) {
      return false;
    }
    return that.isEmptyObj(o) && that.isEmptyObj(n) ||
      Object.keys(o)
        .filter(function (field) {
          return that.props.filterDefs.hasOwnProperty(field);
        })
        .every(function (field) {
          if (o[field] === n[field] || o[field].value === n[field].value) {
              return true;
          }
          if (Array.isArray(o[field]) && Array.isArray(n[field])) {
              return o[field].every(function (oState, index) {
                return oState === n[field][index] ||
                  oState.value === n[field][index].value;
              });
          }
          return false;
        });
  },
  isSameValueArray: function (oArr, nArr) {
    return oArr.every(function (value, index) {
      return value.value === nArr[index].value;
    });
  },
  isEmptyObj: function (obj) {
    return Object.keys(obj).length === 0;
  },
  // 用于在设置了 treeView 选项的 filter state 中寻找已选状态位置
  findIndex: function (arr, value) {
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].value === value.value) {
        return i;
      }
    }
    return -1;
  },

  render: function () {
    var filterNodes = this.props.filterDefs.map(function (def, index) {
      var options = this.state.filterValues[def.field] || [];
      return (
        React.createElement("li", {key: index, style: {display: options.length > 0 ? 'block' : 'none'}}, 
          React.createElement(Filter, {
            name: def.name, 
            field: def.field, 
            canMultiSelect: def.canMultiSelect, 
            treeView: def.treeView, 
            options: options, 
            onSelectOption: this.addFilterState.bind(null, def.field)}
          )
        )
      );
    }.bind(this));

    return (
      React.createElement("div", {className: "cu-filter-group"}, 
        React.createElement(FilterStateBar, {
          filterState: this.state.filterState, 
          getFilterDef: this.getFilterDef, 
          onStateDelete: this.removeFilterState
        }, 
          this.props.children
        ), 
        React.createElement("ul", {className: "filter-group"}, 
          filterNodes
        )
      )
    );
  }
});

'use strict'

//  ==================================================
//  Component: ProgressBar
//
//  Include: PaginationBtn
//
//  TODO:
//  ==================================================

/* PaginationBtn */
var PaginationBtn = React.createClass({displayName: "PaginationBtn",
  getDefaultProps: function() {
    return {
      text: 1,
      type: "num"
    };
  },
  render: function() {
    var text = (this.props.type === 'dot') ? '...' : this.props.text;
    var itemClass = this.props.active
      ? "item active"
      : "item";
    if(this.props.type !== 'num') {
      itemClass += (" page " + this.props.type);
    }
    if(this.props.disabled) {
      itemClass += ' disabled';
    }
    return (
      React.createElement("li", {className: itemClass, onClick: this.props.changePage}, 
        React.createElement("a", null, text)
      )
    );
  }
});

/* Pagination Overview */
var PagiOverview = React.createClass({displayName: "PagiOverview",
  render: function() {
    return (
      React.createElement("div", {className: "overview"}, "共 ", this.props.pages, " 页，")
    );
  }
});

/* Pagination QuickGo */
var PagiQuickGo = React.createClass({displayName: "PagiQuickGo",
  getInitialState: function() {
    return {
      pageInput: null
    };
  },
  inputChange: function(e) {
    this.setState({
      pageInput: e.target.value
    });
  },
  quickGo: function() {
    if(this.state.pageInput) {
      var nextPage = +this.state.pageInput;
      nextPage = nextPage < 1 ? 1 : nextPage;
      nextPage = nextPage > this.props.pages ? this.props.pages : nextPage;
      this.props.setActivePage(nextPage)
    }
  },
  render: function() {
    return (
      React.createElement("div", {className: "quick-go"}, 
        React.createElement("span", null, "到第"), 
        React.createElement("input", {className: "go-page", type: "number", min: "1", max: this.props.pages, onChange: this.inputChange}), 
        React.createElement("span", null, "页"), 
        React.createElement("button", {className: "go-submit", onClick: this.quickGo}, "确认")
      )
    );
  }
});

/* Pagination Main */
var PagiMain = React.createClass({displayName: "PagiMain",
  getInitialState: function() {
    return {
      pageItems: this.getPageItems(this.props.activePage)
    };
  },
  componentWillReceiveProps: function(nextProps) {
    if(nextProps.activePage !== this.props.activePage || nextProps.pages !== this.props.pages) {
      var pageItems = this.getPageItems(nextProps.activePage, nextProps.pages);
      this.setState({
        pageItems: pageItems
      });
      if(nextProps.activePage !== this.props.activePage) {
        this.props.selected(nextProps.activePage);
      }
    }
  },
  handleItemClick: function(type, page) {
    if (type === "first") {
      page = 1;
    } else if (type === "prev") {
      page = (this.props.activePage === 1) ? 1 : this.props.activePage - 1;
    } else if (type === "next") {
      page = (this.props.activePage === this.props.pages) ? this.props.pages : this.props.activePage + 1;
    } else if (type === "last") {
      page = this.props.pages;
    } else {
      page = page > this.props.pages ? this.props.pages : page;
    }
    if (page !== this.props.activePage) {
      this.props.setActivePage(page);
    }
  },
  getPageItems: function(n, pages) {
    var list = [];
    var b = this.props.basePages;
    var m = this.props.midPages;
    var p = pages || this.props.pages;
    if(n <= parseInt(m / 2) + 1) { // 1
      list = this._getSeriesNumber(1, p <= b + m ? p : m);
    } else if((n <= parseInt(m / 2) + 1 + b) || p <= b + m)  { // 1'
      list = this._getSeriesNumber(1, p <= b + m ? p : n + 2);
    } else if((n < p - parseInt(m / 2) - 1)) {  // 2
      list = this._getSeriesNumber(1, this.props.basePages);
      list.push(0);
      list = list.concat(this._getSeriesNumber(n-2, m));
      if(p > m + b + 2) {
        list.push(0);
      }
    } else if(n === p - parseInt(m / 2) - 1) {  // 3
      list = this._getSeriesNumber(1, this.props.basePages);
      list.push(0);
      list = list.concat(this._getSeriesNumber(p - m, m + 1));
    } else {  // 4
      list = this._getSeriesNumber(1, this.props.basePages);
      list.push(0);
      list = list.concat(this._getSeriesNumber(p - m + 1, m));
    }
    return list;
  },
  _getSeriesNumber: function(start, length) {
    start = start;
    length = length;
    var series = [];
    while(length--) {
      series.push(start++);
    }
    return series;
  },
  render: function() {
    var startBlock = [];
    var endBlock = [];
    if(this.props.pages > 0) {
      if(this.props.first) {
        startBlock.push(React.createElement(PaginationBtn, {key: "first", text: this.props.first, disabled: (this.props.activePage === 1) ? true : false, type: "prev", type: "first", changePage: this.handleItemClick.bind(this, 'first')}));
      }
      if(this.props.prev) {
        startBlock.push(React.createElement(PaginationBtn, {key: "prev", text: this.props.prev, disabled: (this.props.activePage === 1) ? true : false, type: "prev", changePage: this.handleItemClick.bind(this, 'prev')}));
      }
      if(this.props.next) {
        endBlock.push(React.createElement(PaginationBtn, {key: "next", text: this.props.next, type: "next", disabled: (this.props.activePage === this.props.pages) ? true : false, changePage: this.handleItemClick.bind(this, 'next')}));
      }
      if(this.props.last) {
        endBlock.push(React.createElement(PaginationBtn, {key: "last", text: this.props.last, type: "last", disabled: (this.props.activePage === this.props.pages) ? true : false, changePage: this.handleItemClick.bind(this, 'last')}));
      }
    }
    return (
      React.createElement("ul", {className: "pagi-main"}, 
        startBlock, 
        
          (this.props.pages > 0) && this.state.pageItems.map(function(item, i) {
              return (
                React.createElement(PaginationBtn, {key: i, text: item, type: item ? 'num' : 'dot', active: (item === this.props.activePage) ? true : false, changePage: item ? this.handleItemClick.bind(this, 'num', item) : null})
              )
            }.bind(this)), 
        
        endBlock
      )
    )
  }
});

/* Pagination */
var Pagination = React.createClass({displayName: "Pagination",
  propTypes: {
    pages: React.PropTypes.number
  },
  getInitialState: function() {
    return {
      activePage: this.props.activePage
    };
  },
  getDefaultProps: function() {
    return {
      activePage: 1, // 激活页初始值
      first: null, // 首页 null || string
      prev: "上一页", // 上一页 null || string
      basePages: 2, // first prev base ... mid ... next last
      midPages: 5, // first prev base ... mid ... next last
      ellipsis: true, // 省略号 boolen
      next: "下一页", // 下一页 null || string
      last: null, // 末页 null || string
      theme: "light", // 主题
      quickGo: false, // 概览和快速切换 boolen
      selected: function(page) { // 页码切换时回调
        console.log(page);
      }
    }
  },
  componentWillReceiveProps: function(nextProps) {
    if(nextProps.activePage !== this.props.activePage) {
      this.setActivePage(nextProps.activePage);
    }
  },
  setActivePage: function(page) {
    this.setState({
      activePage: page
    });
  },
  render: function() {
    var pagiClass = (this.props.theme === 'light') ? 'pagination' : 'pagination ' + this.props.theme;
    return (
      React.createElement("div", {className: pagiClass}, 
        React.createElement(PagiMain, React.__spread({},  this.props, {activePage: this.state.activePage, setActivePage: this.setActivePage})), 
        this.props.quickGo ? React.createElement(PagiOverview, {pages: this.props.pages}) : null, 
        this.props.quickGo ? React.createElement(PagiQuickGo, {pages: this.props.pages, setActivePage: this.setActivePage}) : null
      )
  )
  }
});

'use strict'

//  ==================================================
//  Component: ProgressBar
//
//  Include: Spinner
//
//  Description: Jsx for ProgressBar
//
//  TODO: [fix] 修正初始时 transition 不生效的问题
//  ==================================================

/* Spinner */
var Spinner = React.createClass({displayName: "Spinner",
  render: function() {
    return (
      React.createElement("div", {className: "cu-spinner", style: {borderColor: this.props.color,borderLeftColor: 'transparent'}})
    );
  }
});

/* ProgressBar */
var ProgressBar = React.createClass({displayName: "ProgressBar",
  getInitialState: function() {
    return {
      rate: null,
      done: false
    };
  },
  getDefaultProps: function() {
    return {
      speed: 0.6,  // 动画速度
      spinner: true,  // 是否有圈圈
      easing: 'ease',  // 动画缓动曲线
      maxRate: 0.96,  // 进度条最大宽度
      incStep: 0.04,  // inc 增长步幅
      minStep: 0.005,  // 随机增长的最小步幅
      maxStep: 0.03,  // 随机增长的最大步幅
      trickle: true,  // 是否自动增长
      trickleSpeed: 800,  // 自动增长的间隔时间
      color: '#09c4c7',
      setTrickle: false  // set 后是否自动增长（未启用）
    };
  },
  start: function() {
    this._init();
    this.set('0.5%');
    this.props.trickle && this._autoInc();
  },
  set: function(n, trickle) {
    !trickle && this._init();
    n = this._format(n);
    if (n === 100) {
      /* done */
      this.setState({
        rate: 100
      });
    } else {
      n = n > this.props.maxRate * 100
        ? this.props.maxRate * 100
        : n;
      this.setState({
        rate: n
      });
    }
  },
  inc: function(n) {
    this._init();
    this.props.trickle && this._autoInc();
    n = n
      ? this._format(n)
      : this.props.incStep * 100;
    var newRate = this.state.rate + n;
    this.set(newRate + '%', true);
  },
  done: function() {
    this.set('100%');
    setTimeout(function() {
      this.setState({
        done: true
      });
      setTimeout(function() {
        this.setState({
          rate: null
        });
      }.bind(this), this.props.speed * 2 * 1000);
    }.bind(this), this.props.speed * 1000);
  },
  _format: function(data) {  // 格式化为 0-100 的整数
    if (typeof data === 'number') {  // 0-1 的小数
      return data > 1
        ? this.pros.maxRate * 100
        : data * 100;
    } else if (typeof data === 'string') {  // 百分比
      return parseFloat(data) > 100
        ? this.props.maxRate * 100
        : parseFloat(data);
    } else {
      return;
    }
  },
  _init: function() {
    this.state.done && this.setState({
      done: false
    });
    this.timer && this._clearInterval();
  },
  _autoInc: function() {
    var newRate;
    var random;
    this.timer = setInterval(function() {
      random = this._getRadomStep();
      newRate = this.state.rate + random;
      console.log(random);
      if (newRate > this.props.maxRate * 100) {
        console.log(this.props.maxRate * 100);
        this._clearInterval();
        return;
      }
      console.log(newRate);
      this.set(newRate + '%', true);
    }.bind(this), this.props.trickleSpeed);
  },
  _clearInterval: function() {
    this.timer && clearInterval(this.timer);
  },
  _getRadomStep: function(min, max) {
    min = min || this.props.minStep * 100;
    max = max || this.props.maxStep * 100;
    return Math.random() * (max - min) + min;
  },
  render: function() {
    var progressStyle = {
      //display: (!this.state.rate && typeof this.state.rate === 'object') ? 'none' : 'block',
      opacity: this.state.done
        ? 0
        : 1,
      transition: 'opacity ' + this.props.speed + 's ' + this.props.easing
    };
    var barStyle = {
      width: !this.state.rate
        ? 0
        : this.state.rate + '%',
      transition: 'width ' + this.props.speed + 's ' + this.props.easing,
      backgroundColor: this.props.color,
      boxShadowColor: this.props.color
    };
    return this.state.rate
      ? (
        React.createElement("div", {className: "cu-progress", style: progressStyle}, 
          React.createElement("div", {className: "cu-progress-bar", style: barStyle}), 
          this.props.spinner
            ? React.createElement(Spinner, {color: this.props.color})
            : null
        )
      )
      : null;
  }
});

var ToolTip = React.createClass({displayName: "ToolTip",
    getDefaultProps: function() {
        return {
            tip: "tip",
            trigger: 'hover',
            delay: 0,
            hoverable: false,
            position: "tip",
            width: "200px",
            type: 'span',
            aHref: "#"
        };
    },
    getInitialState: function() {
        return {
            position: this.props.position,
            isActive: false,
            isOnTip: false,
            tipHeight: ""
        };
    },
    handleMouseOver: function(e) {
        if(this.props.trigger=="hover") {
            this.setState({isActive: true});
        }
    },
    handleMouseOut: function(e) {
        if(this.props.trigger=="hover") {
            setTimeout(function() {
                if(this.state.isOnTip) {
                    return false;
                }
                this.setState({isActive: false});
            }.bind(this) , this.props.delay);
        }
    },
    handleClick: function(e) {
        if(this.props.trigger=="click") {
            if(this.state.isActive) {
                this.setState({isActive: false});
            } else if(!this.state.isActive) {
                this.setState({isActive: true});
            }
        }
    },
    handleTipMouseOver: function(e) {
        if(this.props.hoverable) {
            this.setState({isOnTip: true});
            this.setState({isActive: true});
        }
    },
    handleTipMouseOut: function(e) {
        if(this.props.hoverable) {
            this.setState({isOnTip: false});
            this.setState({isActive: false});
        }
    },
    componentDidUpdate: function() {
        this.setTipPosition();
    },
    setTipPosition: function() {
        var tip = this.refs.tip.getDOMNode();
        var cont = this.refs.cont.getDOMNode();
        if(!this.flag) {
            this.state.tipHeight = tip.offsetHeight;
            this.flag = 1;
        }
        var tipWidth = tip.offsetWidth;
        var tipHeight = tip.offsetHeight;
        var contWidth = cont.offsetWidth;
        var contHeight = cont.offsetHeight;
        switch (this.state.position) {
            case "left":tip.style.top = -(tipHeight-contHeight)/2+"px";
                        tip.style.left = -(tipWidth+20)+"px";
                break;
            case "right":tip.style.top = -(tipHeight-contHeight)/2+"px";
                        tip.style.left = "100%";
                break;
            case "top":tip.style.left = -(tipWidth-contWidth)/2+"px";
                        tip.style.bottom = "100%";
                break;
            case "bottom":tip.style.left = -(tipWidth-contWidth)/2+"px";
                        tip.style.top = "100%";
                break;
            default: tip.style.top = -(tipHeight-contHeight)/2+"px";
                    tip.style.left = -(tipWidth+20)+"px";
        }
        tip.style.height = this.state.tipHeight-20+"px";
        this.prevertTipOverflow();
    },
    prevertTipOverflow: function() {
        var tipX = this.refs.tip.getDOMNode().getBoundingClientRect().left;
        var tipY = this.refs.tip.getDOMNode().getBoundingClientRect().top;
        var tipWidth = this.refs.tip.getDOMNode().offsetWidth;
        var tipHeight = this.refs.tip.getDOMNode().offsetHeight;
        var availWidth = parseInt(document.body.clientWidth);
        if(tipX < 0 && tipX+tipWidth > availWidth) {
            return true;
        }
        if(tipX < 0) {
            if(this.state.position == "left") {
                this.setState({position: "top"});
                return ;
            }
            if(this.state.position == "top" || this.state.position == "bottom") {
                this.setState({position: "right"});
                return ;
            }
        }
        if(tipX+tipWidth > availWidth) {
            if(this.state.position == "right") {
                this.setState({position: "bottom"});
                return ;
            }
            if(this.state.position == "bottom" || this.state.position == "top") {
                this.setState({position: "left"});
                return ;
            }
        }

    },
    getTipStyle: function() {
        return {
            display: this.state.isActive?"block":"none",
            color: "pink",
            backgroundColor: "#333",
            width: this.props.width,
        };
    },
    render: function() {
        if(this.props.type=="span") {
            return (
                React.createElement("span", {className: "tooltip "+this.state.position}, 
                    React.createElement("span", {ref: "cont", onMouseOver: this.handleMouseOver, onMouseOut: this.handleMouseOut, onClick: this.handleClick}, this.props.children), 
                    React.createElement("div", {onMouseOver: this.handleTipMouseOver, onMouseOut: this.handleTipMouseOut, className: "tip", ref: "tip", style: this.getTipStyle()}, this.props.tip)
                )
            );
        }
        if(this.props.type=="a") {
            return (
                React.createElement("span", {className: "tooltip "+this.state.position}, 
                    React.createElement("a", {href: this.props.aHref, ref: "cont", onMouseOver: this.handleMouseOver, onMouseOut: this.handleMouseOut, onClick: this.handleClick}, this.props.children), 
                    React.createElement("div", {onMouseOver: this.handleTipMouseOver, onMouseOut: this.handleTipMouseOut, className: "tip", ref: "tip", style: this.getTipStyle()}, this.props.tip)
                )
            );
        }
        if(this.props.type=="button") {
            return (
                React.createElement("span", {className: "tooltip "+this.state.position}, 
                    React.createElement("button", {ref: "cont", onMouseOver: this.handleMouseOver, onMouseOut: this.handleMouseOut, onClick: this.handleClick}, this.props.children), 
                    React.createElement("div", {onMouseOver: this.handleTipMouseOver, onMouseOut: this.handleTipMouseOut, className: "tip", ref: "tip", style: this.getTipStyle()}, this.props.tip)
                )
            );
        }
    }
});
