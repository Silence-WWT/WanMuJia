$(function(){window.location.hash.slice(1);$(".tab .tabs").delegate("li a","click",function(){var a=$(this).parent(),i=a.data("tab");a.siblings().removeClass("active"),a.addClass("active"),window.location.hash=i,a.parent().nextAll(".tab-content").find("."+i).show().siblings().hide()})});