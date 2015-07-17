function setCookie(e,t,a){var i=encodeURIComponent(e)+"="+encodeURIComponent(t);return a instanceof Date&&(i+="; expires="+a.toGMTString()),document.cookie=i}function getCookie(e){var t;return decodeURIComponent(document.cookie).split("; ").forEach(function(a){a=a.split("="),e===a[0]&&(t=a[1])}),t}function convertTimeString(e){if("number"!=typeof e)return"";var t=new Date(1e3*e);return t.getFullYear()+"-"+t.getMonth()+"-"+t.getDay()}function getPageTitle(){return $(".page-title").data("page")}function saveInfos(e){$.ajax({url:e.url,method:e.method,data:e.form.serialize(),success:e.success,error:e.error})}function deleteImage(e){$.ajax({url:"/vendor/item_image",method:"put",data:{image_hash:e}})}function formDirtyCheck(e,t){var a=e.serialize(),i=a!==t;return{isDirty:i,origin:i?a:t}}function genImageView(e){return'<div class="col-md-3 col-sm-4 col-xs-6"><div class="album-image" data-hash="'+e.hash+'"><a href="#" class="thumb" data-action="edit" data-toggle="modal" data-target="#gallery-image-modal"><img src="'+e.url+'" class="img-responsive" /></a><a href="#" class="name"><span>'+e.name+"</span><em>"+convertTimeString(e.created)+'</em></a><div class="image-options"><a href="#" data-action="trash" data-toggle="modal" data-target="#gallery-image-delete-modal"><i class="fa-trash"></i></a></div></div></div>'}function setElemText(e,t){e.is("input")?e.val(t):e.text(t)}function sendEnable(e,t){setElemText(e,t),e.removeClass("disabled")}function sendDisable(e,t,a){var i=parseInt((a-t+parseInt(getCookie("clickTime")))/1e3);e.addClass("disabled"),setElemText(e,i+" 秒后点击再次发送")}function setCountDown(e,t,a){var i=setInterval(function(){Date.now()-getCookie("clickTime")>=a-1e3?(clearTimeout(i),sendEnable(e,t),setCookie("clickTime","",new Date(0))):sendDisable(e,Date.now(),a)},200)}jQuery(document).ready(function(e){e.validator&&(e.validator.addMethod("regex",function(e,t,a){return a.constructor!=RegExp?a=new RegExp(a):a.global&&(a.lastIndex=0),this.optional(t)||a.test(e)},"Please check your input."),e.validator.addMethod("mobile",function(e,t){var a=e.length,i=/^((1[3-8][0-9])+\d{8})$/;return this.optional(t)||11==a&&i.test(e)}),e.validator.addMethod("tel",function(e,t){var a=/^\d{3,4}-?\d{7,9}$/;return this.optional(t)||a.test(e)}));var t=e("#img-upload.dropzone");t.length>0&&t.dropzone({url:"/vendor/items/image",method:"put",acceptedFiles:"image/jpg, image/jpeg, image/png",addRemoveLinks:"item-edit"!==getPageTitle(),dictDefaultMessage:"拖动文件到此以上传",dictResponseError:"服务器错误, 上传失败, 请稍后重试。",dictCancelUpload:"取消上传",dictCancelUploadConfirmation:"确定取消上传吗？",dictRemoveFile:"移除文件",init:function(){this.on("removedfile",function(t){console.log(t.previewElement);var a=e(t.previewElement).data("hash");a&&deleteImage(a)}).on("success",function(t,a){e(t.previewElement).data("hash",a.hash);var i=e(".album-images");i.length>0&&i.append(e(genImageView({name:t.name,hash:a.hash,url:a.url,created:a.created})))})}});if("item-edit"===getPageTitle()){var a=e("#edit-item-form"),i=a.serialize();a.delegate(".form-control","keydown",function(){e("#save").next().hide()}),a.find("select").click(function(){console.log("clicked"),e("#save").next().hide()}),e("#save").click(function(){var t=e(this);if(!t.hasClass("disabled")){var s=formDirtyCheck(a,i);s.isDirty&&saveInfos({url:window.location.pathname,method:"put",form:a,success:function(){t.next().text("保存成功！").addClass("text-success").removeClass("text-danger").show(),i=s.origin},error:function(){t.next().text("服务器错误，请稍后重试").removeClass("text-success").addClass("text-danger").show()}})}});var s=e(".album-images"),r="";s.delegate('[data-action="trash"]',"click",function(){console.log("delete"),r=e(this).parents(".album-image").data("hash")}).delegate(".album-image","click",function(){var t=e(this).find(".thumb img").attr("src");e("#gallery-image-modal").find("img").attr("src",t)}),e("#gallery-image-delete-modal").find("#delete").click(function(){s.find("[data-hash="+r+"]").parent().remove(),deleteImage(r)}),e("#sort-confirm").click(function(){var t=[];s.find(".album-image").each(function(){t.push(e(this).data("hash"))}),e.ajax({url:"/items/image_sort",method:"post",data:t.join(",")})})}if("item-new"===getPageTitle()){var n=e("#new-item-form"),o=function(){var t=e(this);if(!t.hasClass("disabled")){if(n.hasClass("validate")){var a=n.valid();if(!a)return void n.data("validator").focusInvalid()}var i=t.children("a"),s=i.html();t.addClass("disabled"),i.html('<span class="fa fa-spin fa-spinner"></span>'),saveInfos({url:"/vendor/items/new_item",method:"post",form:e("#new-item-form"),success:function(e){e.success?n.bootstrapWizard("next"):toastr.error(e.message,"提交失败"),i.html(s),t.removeClass("disabled")}})}};e(".wizard .next").off("click").click(o)}if("distributors"===getPageTitle()&&e("#distributors").delegate('[data-target="#revocation-modal"]',"click",function(){var t=e(this).data("dist-id"),a=e("#contract-form"),i=a.attr("action").split("/");i[3]=t,a.attr("action",i.join("/"))}),"dist-invitation"===getPageTitle()&&e("#get-key").click(function(){e.ajax({url:"/vendor/distributors/invitation",method:"post",success:function(t){e(".invite-key").text(t)},error:function(){}})}),"settings"===getPageTitle()&&(e("#logo").on("change",function(){var t=e(this),a=this.files?this.files:[];if(!(a.length<=0)&&window.FileReader&&/^image/.test(a[0].type)){var i=new FileReader;i.readAsDataURL(a[0]),i.onloadend=function(){t.siblings(".logo-preview").find("img").attr("src",this.result)}}}),e("#contact_mobile").rules("add",{mobile:!0,messages:{mobile:"请填写合法的手机号码"}}),e("#contact_telephone").rules("add",{tel:!0,messages:{tel:"请填写合法的固定电话号码"}})),"register"==e("body").data("page")){var d=e(".send"),l=6e4,c=d.val()||d.text();getCookie("clickTime")&&(console.log(getCookie("clickTime")),console.log("get click time"),sendDisable(d,Date.now(),l),setCountDown(d,c,l)),d.click(function(){var t=e(this);t.hasClass("disabled")||(setCookie("clickTime",Date.now()),e.ajax({url:"/service/mobile_register_sms",method:"post",data:{contact_mobile:e("#contact_moblie").val()}}),setCountDown(t,c,l))})}"register-next"==e("body").data("page")&&(e("#email").rules("add",{required:!0,email:!0,messages:{required:"请输入您的邮箱",email:"请输入合法的邮箱地址"}}),e("#password").rules("add",{required:!0,regex:/^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z]{6,}$/,messages:{required:"请设置密码",regex:"密码长度必须大于等于6位且为字母和数字的组合"}}),e("#confirm_password").rules("add",{required:!0,equalTo:"#password",messages:{required:"请再次输入密码",equalTo:"两次密码输入不一致"}}),e("#agent_name").rules("add",{required:!0,messages:{required:"请输入代理人姓名"}}),e("#agent_identity").rules("add",{required:!0,regex:/^\d{15}(\d\d[0-9xX])?$/,messages:{required:"请输入代理人身份证",regex:"不合法的身份证号码"}}),e("#agent_identity_photo_front").rules("add",{required:!0,messages:{required:"请上传代理人身份证正面照片"}}),e("#agent_identity_photo_back").rules("add",{required:!0,messages:{required:"请上传代理人身份证反面照片"}}),e("#name").rules("add",{required:!0,messages:{required:"请填写厂家名称"}}),e("#license_address").rules("add",{required:!0,messages:{required:"请填写营业执照所在地"}}),e("#limit").rules("add",{required:!0,messages:{required:"请填写营业期限"}}),e("#province_cn_id").rules("add",{required:!0,messages:{required:"请选择省级行政区"}}),e("#city_cn_id").rules("add",{required:!0,messages:{required:"请选择市级行政区"}}),e("#district_cn_id").rules("add",{required:!0,messages:{required:"请选择区级行政区"}}),e("#address").rules("add",{required:!0,messages:{required:"请填写联系地址"}}))});