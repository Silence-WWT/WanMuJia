$(function(){var t,a=$(".gallery .thumbnail"),e=200;a.delegate("li","mouseenter",function(){var a=$(this),o=a.find("img").attr("src");t=setTimeout(function(){$(".booth img").attr("src",o),a.siblings().removeClass("active"),a.addClass("active")},e)}),a.delegate("li","mouseleave",function(){t&&clearTimeout(t)});var o="/collection",r=$(".property .action .like"),i=$(".property .action .vs"),s=$(".addvs-tip-ball");i.click(function(t){var a=$(this),e=a.attr("data-id");if(CompareBarCom.addItem(e)){s.show();var o=t.pageX,r=t.pageY,i=$("#comparebar_link").offset().left+24,n="2px";s.css({left:o,top:r}),s.animate({left:i,top:n},350,function(){s.hide()})}}),r.click(function(){var t=$(this),a=t.attr("data-id"),e=t.attr("data-method");t.attr("disabled",!0),$.ajax({method:e,url:o,dataType:"json",data:{item:a},success:function(a){t.attr("disabled",!1),a.success?"POST"==e?(t.text("取消收藏"),t.attr("data-method","DELETE")):"DELETE"==e&&(t.text("收藏"),t.attr("data-method","POST")):!a.success},error:function(t,a,e){console.error(o,a,e.toString())}})});var n="/login",c=$(".login_btn"),l=$("#username"),d=$("#password"),u=$("#csrf_token");c.click(function(t){return t.preventDefault(),l.val()&&d.val()?($(this).attr("disabled",!0),void $.ajax({type:"POST",url:n,data:{csrf_token:u.val(),username:l.val(),password:encrypt(d.val())},success:function(t){c.removeAttr("disabled"),t.success?window.location.reload():alert(t.message)},error:function(t,a,e){console.error(n,a,e.toString())}})):console.log("000000000")})});