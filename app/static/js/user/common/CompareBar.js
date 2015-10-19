var CompareBar=React.createClass({displayName:"CompareBar",getInitialState:function(){return{itemData:[],addResult:null,contShow:!1}},getData:function(t){var e="/item/"+t+"?format=json";$.ajax({url:e,dataType:"json",success:function(e){var a=[];a[0]={id:t,data:e},1==this.state.itemData.length&&(a[0]=this.state.itemData[0],a[1]={id:t,data:e}),this.setState({itemData:a})}.bind(this),error:function(t,a,s){console.error(e,a,s.toString())}.bind(this)})},deleteItem:function(t){if(this.props.setCompareItem.deleteItem(t),1==this.state.itemData.length&&this.state.itemData[0].id==t)this.setState({itemData:[]});else if(2==this.state.itemData.length){var e=[];this.state.itemData[0].id==t?(e[0]=this.state.itemData[1],this.setState({itemData:e})):this.state.itemData[1].id==t&&(e[0]=this.state.itemData[0],this.setState({itemData:e}))}},addItem:function(t){var e=this.props.setCompareItem.addItem(t);this.setState({addResult:e});var a=2e3;return setTimeout(function(){this.setState({contShow:!0})}.bind(this),500),setTimeout(function(){this.setState({contShow:!1}),this.setState({addResult:null})}.bind(this),a+2500),e.success?(setTimeout(this.getData(t),a),!0):!1},componentWillMount:function(){for(var t=this.props.setCompareItem.getItem(),e=0;e<t.length;e++)this.getData(t[e])},render:function(){return React.createElement("div",{className:"compare-bar"},React.createElement("a",{href:"/compare",target:"_blank",id:"comparebar_link"},"对比"),this.state.itemData.length?React.createElement("span",{className:"compare-num",id:"comparebar_num"},this.state.itemData.length):null,React.createElement(CompareBarCont,{addResult:this.state.addResult,contShow:this.state.contShow,itemData:this.state.itemData,deleteItem:this.deleteItem}))}}),CompareBarCont=React.createClass({displayName:"CompareBarCont",render:function(){var t=[],e=this.props.itemData;return 0===e.length?t[0]=React.createElement("div",{className:"tip-to-add all-no"},"当前没有可以对比的选项，您可以到商品详情页添加要对比的商品"):1==e.length?(t[0]=React.createElement(CompareBarItem,{data:e[0],deleteItem:this.props.deleteItem}),t[1]=React.createElement("div",{className:"tip-to-add"},"您还可以继续添加要对比的商品")):2==e.length&&(t[0]=React.createElement(CompareBarItem,{data:e[0],deleteItem:this.props.deleteItem}),t[1]=React.createElement(CompareBarItem,{data:e[1],deleteItem:this.props.deleteItem}),t[2]=React.createElement("a",{className:"compare-link",href:"/compare",target:"_blank"},"对比")),React.createElement("div",{className:"compare-bar-cont",style:this.props.contShow?{display:"block"}:{}},this.props.addResult?React.createElement("div",{className:"add-result-tip "+this.props.addResult.success},this.props.addResult.msg):null,t)}}),CompareBarItem=React.createClass({displayName:"CompareBarItem",handleDelClick:function(){this.props.deleteItem(this.props.data.id)},render:function(){return React.createElement("div",{className:"compare-bar-item"},React.createElement("img",{alt:this.props.data.data.item,src:this.props.data.data.image_url}),React.createElement("div",{className:"desc"},React.createElement("h2",null,this.props.data.data.item),React.createElement("div",{className:"price"},"¥"+this.props.data.data.price)),React.createElement("span",{onClick:this.handleDelClick,className:"delete"},"删除"))}}),CompareBarCom=React.render(React.createElement(CompareBar,{setCompareItem:setCompareItem}),document.getElementById("compareBar"));