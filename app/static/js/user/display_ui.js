$(function(){function e(e,r){"popstate"!==r&&"pagination"!==r&&(e.page=1),getSearchData({params:e,done:function(e){var i=e.filters;a=genUrlQuery({filterSelected:i.selected,otherParams:e.items}),$("#amount").text(e.items.amount),p.setItems(e.items.query),l.updateFilterValue(filterValuesMapping(i.available)),o(e.items.order),c=f(e.items.pages,e.items.page),"popstate"!==r&&t.addHistory(a,"?"+$.param(a,!0)),"popstate"===r&&l.setFilterState(filterValuesMapping(i.selected))},fail:function(){},beforeSend:function(){i.start()},complete:function(){i.done()}})}var t,a=null,i=React.render(React.createElement(ProgressBar,{color:"#009966"}),$("#progress-bar")[0]),r=[{name:"材料",field:"material",canMultiSelect:!0},{name:"风格",field:"style",canMultiSelect:!0},{name:"场景",field:"scene",canMultiSelect:!0},{name:"种类",field:"category",canMultiSelect:!0},{name:"品牌",field:"brand",canMultiSelect:!0},{name:"价格",field:"price"}],s=[],n=function(t){console.log("state change:",t),e(genUrlQuery({filterSelected:t,otherParams:a,isFromFilter:!0}),"filter")},l=React.render(React.createElement(FilterGroup,{filterDefs:r,filterValues:s,onStateChange:n},React.createElement("span",null,"所有分类 > 共 ",React.createElement("span",{id:"amount"},"0")," 个商品")),$("#filter-group")[0]);t=new HistoryWatcher(function(t){console.log("history changed:",t.state),e(t.state,!0,"popstate")}),$(".sortbar .sort").delegate(".sort-index","click",function(){var t=$(this),i=null,r=null;return t.siblings().removeClass("active"),t.addClass("active"),"hot"!=t.attr("data-sort")&&(i=t.children(".darr"),i.toggleClass("inc").show()),r=i.hasClass("inc")?"asc":"desc",e($.extend({},a,{order:r}),"sortbar"),!1});var c,o=function(e){var t=$('[data-sort="price"]'),a=t.find(".darr");e?"asc"==e?(t.addClass("active"),a.addClass("inc").show()):(t.addClass("active"),a.removeClass("inc").show()):(t.removeClass(".active"),a.hide())},m=React.createClass({displayName:"Item",render:function(){return React.createElement("div",{className:"item","data-id":this.props.item.item_id},React.createElement("a",{href:"/item/"+this.props.item.id},React.createElement("img",{src:this.props.item.image_url,alt:this.props.item.item})),React.createElement("div",{className:"item-info"},React.createElement("h5",null,React.createElement("a",{href:"/item/"+this.props.item.id},this.props.item.item)),React.createElement("div",{className:"price"},"¥ ",this.props.item.price)))}}),d=React.createClass({displayName:"Items",getInitialState:function(){return{filteredItems:[]}},setItems:function(e){this.setState({filteredItems:e})},render:function(){return React.createElement("div",{className:"item-wrapper clearfix"},this.state.filteredItems.map(function(e,t){return React.createElement(m,{item:e,key:t})}))}}),p=React.render(React.createElement(d,null),$("#items")[0]),u=function(t){e($.extend({},a,{page:t}),"pagination")},f=function(e,t){return React.render(React.createElement(Pagination,{pages:e,activePage:t||1,selected:u,theme:"dark",quickGo:!0}),$("#paging")[0])};!function(){getSearchData({done:function(e){a=genUrlQuery({filterSelected:e.filters.selected,otherParams:e.items}),$("#search-input").val(decodeURIComponent(a.search)),$("#amount").text(e.items.amount||""),p.setItems(e.items.query),l.updateFilterValue(filterValuesMapping(e.filters.available)),l.setFilterState(filterValuesMapping(e.filters.selected)),o(e.items.order),c=f(e.items.pages,e.items.page)},fail:function(){}})}()});