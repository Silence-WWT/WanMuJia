function setCookie(e,t,a){var i=encodeURIComponent(e)+"="+encodeURIComponent(t);return a instanceof Date&&(i+="; expires="+a.toGMTString()),document.cookie=i}function getCookie(e){var t;return decodeURIComponent(document.cookie).split("; ").forEach(function(a){a=a.split("="),e===a[0]&&(t=a[1])}),t}function convertTimeString(e){if("number"!=typeof e)return"";var t=new Date(1e3*e);return t.getFullYear()+"-"+t.getMonth()+"-"+t.getDay()}function getPageTitle(){return $(".page-title").data("page")}function saveInfos(e){$.ajax({url:e.url,method:e.method,data:e.form.serialize(),success:e.success,error:e.error})}function deleteImage(e){$.ajax({url:"/vendor/item_image",method:"put",data:{image_hash:e}})}function formDirtyCheck(e,t){var a=e.serialize(),i=a!==t;return{isDirty:i,origin:i?a:t}}function genImageView(e){return'<div class="col-md-3 col-sm-4 col-xs-6"><div class="album-image" data-hash="'+e.hash+'"><a href="#" class="thumb" data-action="edit" data-toggle="modal" data-target="#gallery-image-modal"><img src="'+e.url+'" class="img-responsive" /></a><a href="#" class="name"><span>'+e.name+"</span><em>"+convertTimeString(e.created)+'</em></a><div class="image-options"><a href="#" data-action="trash" data-toggle="modal" data-target="#gallery-image-delete-modal"><i class="fa-trash"></i></a></div></div></div>'}function setElemText(e,t){e.is("input")?e.val(t):e.text(t)}function sendEnable(e,t){setElemText(e,t),e.removeClass("disabled")}function sendDisable(e,t,a){var i=parseInt((a-t+parseInt(getCookie("clickTime")))/1e3);e.addClass("disabled"),setElemText(e,i+" 秒后点击再次发送")}function setCountDown(e,t,a){var i=setInterval(function(){Date.now()-getCookie("clickTime")>=a-1e3?(clearTimeout(i),sendEnable(e,t),setCookie("clickTime","",new Date(0))):sendDisable(e,Date.now(),a)},200)}jQuery(document).ready(function(e){if("item-edit"===getPageTitle()){var t=e("#edit-item-form"),a=t.serialize();t.delegate(".form-control","keydown",function(){e("#save").next().hide()}),t.find("select").click(function(){console.log("clicked"),e("#save").next().hide()}),e("#save").click(function(){var i=e(this);if(!i.hasClass("disabled")){var o=formDirtyCheck(t,a);o.isDirty&&saveInfos({url:window.location.pathname,method:"put",form:t,success:function(){i.next().text("保存成功！").addClass("text-success").removeClass("text-danger").show(),a=o.origin},error:function(){i.next().text("服务器错误，请稍后重试").removeClass("text-success").addClass("text-danger").show()}})}});var i=e(".album-images"),o="";i.delegate('[data-action="trash"]',"click",function(){console.log("delete"),o=e(this).parents(".album-image").data("hash")}).delegate(".album-image","click",function(){var t=e(this).find(".thumb img").attr("src");e("#gallery-image-modal").find("img").attr("src",t)}),e("#gallery-image-delete-modal").find("#delete").click(function(){i.find("[data-hash="+o+"]").parent().remove(),deleteImage(o)}),e("#sort-confirm").click(function(){var t=[];i.find(".album-image").each(function(){t.push(e(this).data("hash"))}),e.ajax({url:"/items/image_sort",method:"post",data:t.join(",")})})}if("item-new"===getPageTitle()){var n=e("#new-item-form"),s=function(){saveInfos({url:"/vendor/items/new_item",method:"post",form:e("#new-item-form"),success:function(){n.bootstrapWizard("next")}})};e(".wizard .next").off("click").click(s),e('[href="#fwv-2"]').off("click").click(s)}if("distributors"===getPageTitle()&&e("#distributors").delegate('[data-target="#revocation-modal"]',"click",function(){var t=e(this).data("dist-id"),a=e("#contract-form"),i=a.attr("action").split("/");i[3]=t,a.attr("action",i.join("/"))}),"dist-invitation"===getPageTitle()&&e("#get-key").click(function(){e.ajax({url:"/vendor/distributors/invitation",method:"post",success:function(t){e(".invite-key").text(t)},error:function(){}})}),"settings"===getPageTitle()&&(e("#logo").on("change",function(){var t=e(this),a=this.files?this.files:[];if(!(a.length<=0)&&window.FileReader&&/^image/.test(a[0].type)){var i=new FileReader;i.readAsDataURL(a[0]),i.onloadend=function(){t.siblings(".logo-preview").find("img").attr("src",this.result)}}}),e("#contact_mobile").rules("add",{mobile:!0,messages:{mobile:"请填写合法的手机号码"}}),e("#contact_telephone").rules("add",{tel:!0,messages:{tel:"请填写合法的固定电话号码"}})),"register"==e("body").data("page")){var r=e(".send"),l=6e4,c=r.val()||r.text();getCookie("clickTime")&&(console.log(getCookie("clickTime")),console.log("get click time"),sendDisable(r,Date.now(),l),setCountDown(r,c,l)),r.click(function(){var t=e(this);t.hasClass("disabled")||(setCookie("clickTime",Date.now()),e.ajax({url:"/send_sms",method:"post",data:{mobile:e("#contact_moblie").val()}}),setCountDown(t,c,l))})}e.validator&&(e.validator.addMethod("mobile",function(e,t){var a=e.length,i=/^((1[3-8][0-9])+\d{8})$/;return this.optional(t)||11==a&&i.test(e)}),e.validator.addMethod("tel",function(e,t){var a=/^\d{3,4}-?\d{7,9}$/;return this.optional(t)||a.test(e)}));var d=e("#img-upload.dropzone");d.length>0&&d.dropzone({url:"/vendor/item_image",method:"put",acceptedFiles:"image/jpg, image/jpeg, image/png",addRemoveLinks:"item-edit"!==getPageTitle(),dictDefaultMessage:"拖动文件到此以上传",dictResponseError:"服务器错误, 上传失败, 请稍后重试。",dictCancelUpload:"取消上传",dictCancelUploadConfirmation:"确定取消上传吗？",dictRemoveFile:"移除文件",init:function(){this.on("removedfile",function(t){console.log(t.previewElement);var a=e(t.previewElement).data("hash");a&&deleteImage(a)}).on("success",function(t,a){e(t.previewElement).data("hash",a.hash);var i=e(".album-images");i.length>0&&i.append(e(genImageView({name:t.name,hash:a.hash,url:a.url,created:a.created})))})}})});