function isObject(e){return e instanceof Object}function isArray(e){return Array.isArray?Array.isArray(e):e instanceof Array}function isFunction(e){return e instanceof Function}function getRegs(){return{email:/^[A-Za-z\d]+([-_.][A-Za-z\d]+)*@([A-Za-z\d]+[-.])+[A-Za-z\d]{2,5}$/,mobile:/^((1[3-8][0-9])+\d{8})$/,captcha:/^\d{6}$/,nickname:/^(?!\d+$)[\u4e00-\u9fa5A-Za-z\d_]{4,30}$/,tel:/^\d{3,4}-?\d{7,9}$/,identity:/^\d{15}(\d\d[0-9xX])?$/,password:/^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z]{6,}$/,userPassword:/^[0-9A-Za-z_.]{6,16}$/,date:/^(\d{4})\/((0?([1-9]))|(1[0|1|2]))\/((0?[1-9])|([12]([0-9]))|(3[0|1]))$/}}function setCookie(e,t,o){var n=encodeURIComponent(e)+"="+encodeURIComponent(t);return o instanceof Date&&(n+="; expires="+o.toUTCString()),document.cookie=n}function getCookie(e){var t;return decodeURIComponent(document.cookie).split("; ").forEach(function(o){o=o.split("="),e===o[0]&&(t=o[1])}),t}function queryStringToJson(e){var t={};return e.split("&").forEach(function(e){var o=e.split("=")[0],n=e.split("=")[1];t[o]=n}),t}function encrypt(e){return hex_md5(hex_md5(e))}function genFormData(e,t){var o={};return e.find("input").each(function(){var e=null;"button"!=this.type&&"submit"!=this.type&&"reset"!=this.type&&("password"==this.type&&this.value.length>0?e=encrypt(this.value):"file"==this.type&&void 0!==t?(console.log(t),e=t[this.name]):e=this.value,o[this.name]=e)}),e.find("select").each(function(){o[this.name]=this.value}),e.find("textarea").each(function(){o[this.name]=this.value}),o}function setFormPending(e){e.data("pending",!0)}function setFormReady(e){e.data("pending",!1)}function getFormState(e){return e.data("pending")}var setCompareItem={getCookie:function(e){for(var t=document.cookie,o=t.split("; "),n=0;n<o.length;n++){var i=o[n].split("=");if(e==i[0])return i[1]}return!1},addItem:function(e){return getCookie("compareItem1")==e||getCookie("compareItem2")==e?{success:!1,msg:"该商品已在对比栏，无法重复添加"}:getCookie("compareItem1")?getCookie("compareItem2")?{success:!1,msg:"对比栏最多只能添加两个商品，请从上方对比栏处进入对比页或重新设置对比商品"}:(setCookie("compareItem2",e),{success:!0,msg:"添加成功"}):(setCookie("compareItem1",e),{success:!0,msg:"添加成功"})},deleteItem:function(e){var t=new Date;t.setTime(t.getTime()-1e4),getCookie("compareItem1")==e?setCookie("compareItem1",0,t):getCookie("compareItem2")==e&&setCookie("compareItem2",0,t)},getItem:function(){var e=[],t=0;return getCookie("compareItem1")&&(e[t]=getCookie("compareItem1"),t++),getCookie("compareItem2")&&(e[t]=getCookie("compareItem2")),e}};