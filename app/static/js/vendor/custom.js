function setCookie(e,t,a){var s=encodeURIComponent(e)+"="+encodeURIComponent(t);return a instanceof Date&&(s+="; expires="+a.toGMTString()),document.cookie=s}function getCookie(e){var t;return decodeURIComponent(document.cookie).split("; ").forEach(function(a){a=a.split("="),e===a[0]&&(t=a[1])}),t}function convertTimeString(e){if("number"!=typeof e)return"";var t=new Date(1e3*e);return t.getFullYear()+"-"+(t.getMonth()+1)+"-"+t.getDate()}function getPageTitle(){return $(".page-title").data("page")}function saveInfos(e){$.ajax({url:e.url,method:e.method,data:e.form.serialize(),success:e.success,error:e.error})}function deleteImage(e,t){$.ajax({url:"/vendor/items/image",method:"delete",data:{image_hash:e},success:t})}function formDirtyCheck(e,t){var a=e.serialize(),s=a!==t;return{isDirty:s,origin:s?a:t}}function genImageView(e,t){return console.log(t),'<div class="col-md-3 col-sm-4 col-xs-6 '+(t?"ui-sortable-handle":"")+'"><div class="album-image" data-hash="'+e.hash+'"><a href="#" class="thumb" data-action="edit" data-toggle="modal" data-target="#gallery-image-modal"><img src="'+e.url+'" class="img-responsive" /></a><a href="#" class="name"><span>'+e.name+"</span><em>"+convertTimeString(e.created)+'</em></a><div class="image-options"><a href="#" data-action="trash" data-toggle="modal" data-target="#gallery-image-delete-modal"><i class="fa-trash"></i></a></div></div></div>'}function setElemText(e,t){e.is("input")?e.val(t):e.text(t)}function sendEnable(e,t){setElemText(e,t),e.removeClass("disabled")}function sendDisable(e,t,a){var s=parseInt((a-t+parseInt(getCookie("clickTime")))/1e3);e.addClass("disabled"),setElemText(e,s+" 秒后点击再次发送")}function setCountDown(e,t,a){var s=setInterval(function(){Date.now()-getCookie("clickTime")>=a-1e3?(clearTimeout(s),sendEnable(e,t),setCookie("clickTime","",new Date(0))):sendDisable(e,Date.now(),a)},200)}function setButtonLoading(e){e.addClass("disabled").html('<i><span class="fa fa-spin fa-spinner"></span></i>')}function resetButton(e,t){e.removeClass("disabled").html(t)}function checkValidate(e,t){if(e.hasClass("validate")){var a=null,s=e.find(t);if(t){if(!(s.length>0))return;a=s.valid()}else a=e.valid();if(!a)return e.data("validator").focusInvalid(),!1}return!0}jQuery(document).ready(function(e){function t(e,t){e.dataTable({aLengthMenu:[[10,25,50,100,-1],[10,25,50,100,"All"]],language:{sProcessing:"处理中...",sLengthMenu:"显示 _MENU_ 项结果",sZeroRecords:"没有匹配结果",sInfo:"显示第 _START_ 至 _END_ 项结果，共 _TOTAL_ 项",sInfoEmpty:"显示第 0 至 0 项结果，共 0 项",sInfoFiltered:"(由 _MAX_ 项结果过滤)",sInfoPostFix:"",sSearch:"搜索:",sUrl:"",sEmptyTable:"表中数据为空",sLoadingRecords:"载入中...",sInfoThousands:",",oPaginate:{sFirst:"首页",sPrevious:"上页",sNext:"下页",sLast:"末页"},oAria:{sSortAscending:": 以升序排列此列",sSortDescending:": 以降序排列此列"}},processing:!0,serverSide:!0,ajax:t.ajax,columns:t.columns,columnDefs:t.columnDefs})}e.validator&&(e.validator.addMethod("regex",function(e,t,a){return a.constructor!=RegExp?a=new RegExp(a):a.global&&(a.lastIndex=0),this.optional(t)||a.test(e)},"Please check your input."),e.validator.addMethod("mobile",function(e,t){var a=e.length,s=/^((1[3-8][0-9])+\d{8})$/;return this.optional(t)||11==a&&s.test(e)}),e.validator.addMethod("tel",function(e,t){var a=/^\d{3,4}-?\d{7,9}$/;return this.optional(t)||a.test(e)}),e.validator.addMethod("identity",function(e,t){var a=/^\d{15}(\d\d[0-9xX])?$/;return this.optional(t)||a.test(e)}),e.validator.addMethod("password",function(e,t){var a=/^(?![0-9]+$)(?![a-zA-Z]+$)[0-9A-Za-z]{6,}$/;return this.optional(t)||a.test(e)}),e.validator.addMethod("customDate",function(e,t){var a=/^(\d{4})\/((0?([1-9]))|(1[0|1|2]))\/((0?[1-9])|([12]([0-9]))|(3[0|1]))$/;return this.optional(t)||a.test(e)}));var a={initDropzone:function(t,a){t.dropzone({url:a.url,method:"put",acceptedFiles:"image/jpg, image/jpeg, image/png",addRemoveLinks:"item-edit"!==getPageTitle(),dictDefaultMessage:"拖动文件到此以上传",dictResponseError:"服务器{{ statusCode }}错误, 上传失败, 请稍后重试。",dictCancelUpload:"取消上传",dictCancelUploadConfirmation:"确定取消上传吗？",dictRemoveFile:"移除文件",init:function(){this.on("removedfile",function(t){var a=e(t.previewElement).data("hash");a&&deleteImage(a)}).on("success",a.success)}})},setPreviewError:function(t,a){e(t.previewElement).removeClass("dz-success").addClass("dz-error").find(".dz-error-message span").text("上传失败!"+a)}};if("items"===getPageTitle()){var s=e("#delete-confirm-form");t(e("#items"),{ajax:"/vendor/items/datatable",columns:[{data:"id",bSortable:!1,visible:!1},{data:"item",bSortable:!1},{data:"second_category_id",bSortable:!1},{data:"price"},{data:"size",bSortable:!1}],columnDefs:[{targets:[5],data:"id",render:function(e){return"<a href='/vendor/items/"+e+"'>详情/编辑</a>"}},{targets:[6],data:{},render:function(e){return'<a href="javascript:void(0)" data-item="'+e.item+'" data-item-id="'+e.id+'" data-toggle="modal" data-target="#delete-confirm-modal">删除商品</a>'}}]}),e("#items").delegate('[data-target="#delete-confirm-modal"]',"click",function(){var t=e(this),a=t.data("item-id"),i=t.data("item");s.data("item-id",a),e("#modal-item-name").text(i)}),e("#modal-item-delete").click(function(t){e.ajax({url:"/vendor/items/"+s.data("item-id"),method:"delete",success:function(){window.location.reload()},error:function(){window.location.reload()}}),t.preventDefault()})}if("item-edit"===getPageTitle()){var i=e("#edit-item-form"),r=i.serialize();i.find(".return-list a").off("click"),i.delegate(".form-control","keydown",function(){e("#save").next().hide()}),i.find("select").click(function(){e("#save").next().hide()}),e("#save").click(function(){var t=e(this),a=t.html();if(!t.hasClass("disabled")){var s=formDirtyCheck(i,r);s.isDirty?(setButtonLoading(t),saveInfos({url:window.location.pathname,method:"put",form:i,success:function(e){e.success?toastr.success("保存成功!"):toastr.error(e.message,"提交失败!"),r=s.origin,resetButton(t,a)},error:function(e){toastr.error("服务器"+e.status+"错误","提交失败!"),resetButton(t,a)}})):toastr.warning("没有修改内容!")}});var o=e(".album-images"),n=function(){var t=[];return o.find(".album-image").each(function(){t.push(e(this).data("hash"))}),t},d=n();a.initDropzone(e("#img-upload"),{url:"/vendor/items/image?item_id="+i.data("item-id"),success:function(t,s){var i=e(t.previewElement);if(s.success){var r=s.image;i.data("hash",r.hash),o.length>0&&(o.append(e(genImageView({name:t.name,hash:r.hash,url:r.url,created:r.created},o.hasClass("ui-sortable")?!0:!1))),d.push(r.hash))}else a.setPreviewError(t,s.message)}});var l="";o.delegate('[data-action="trash"]',"click",function(){l=e(this).parents(".album-image").data("hash")}).delegate(".album-image","click",function(){var t=e(this).find(".thumb img").attr("src");e("#gallery-image-modal").find("img").attr("src",t)}),e("#gallery-image-delete-modal").find("#delete").click(function(){o.find("[data-hash="+l+"]").parent().remove(),deleteImage(l,function(e){if(e.success){var t=d.indexOf(deleteImage);d.splice(t,1)}})}),e("#sort-confirm").click(function(){var t=n();console.log(d,t),t.toString()==d.toString()?toastr.success("保存顺序成功!"):e.ajax({url:"/vendor/items/image_sort",method:"post",data:{item_id:i.data("item-id"),images:t.join(",")},success:function(e){e.success?(toastr.success("保存顺序成功!"),d=t):toastr.error(e.message,"保存顺序失败! 请重新保存~")},error:function(e){toastr.error("服务器"+e.status+"错误...","保存顺序失败! 请重新保存~")}})})}if("item-new"===getPageTitle()){var c=e("#new-item-form"),u=function(){var t=e(this);if(!t.hasClass("disabled")&&checkValidate(c)){var s=t.children("a"),i=s.html();t.addClass("disabled"),s.html('<i><span class="fa fa-spin fa-spinner"></span></i>'),saveInfos({url:"/vendor/items/new_item",method:"post",form:e("#new-item-form"),success:function(r){r.success?(toastr.success("您可以继续添加商品图片","商品添加成功!"),a.initDropzone(e("#img-upload"),{url:"/vendor/items/image?item_id="+r.item_id,success:function(t,s){var i=e(t.previewElement);if(s.success){var r=s.image;i.data("hash",r.hash)}else a.setPreviewError(t,s.message)}}),c.bootstrapWizard("next"),t.hide(),c.find(".add-another").show().children("a").off("click"),c.find(".return-list").show().children("a").off("click")):(toastr.error(r.message,"提交失败"),t.removeClass("disabled")),s.html(i)},error:function(e){toastr.error("服务器"+e.status+"错误","提交失败"),s.html(i),t.removeClass("disabled")}})}};e(".wizard .next").off("click").click(u)}if("distributors"===getPageTitle()){var m=e("#distributors");t(m,{ajax:"/vendor/distributors/datatable",columns:[{data:"id",bSortable:!1,visible:!1},{data:"name"},{data:"address",bSortable:!1},{data:"contact_telephone",bSortable:!1},{data:"contact_mobile",bSortable:!1},{data:"contact",bSortable:!1},{data:"created"},{data:"revocation_state",visible:!1}],columnDefs:[{targets:[8],data:{},render:function(e){var t=function(t){return'<a href="javascript:void(0)" data-toggle="modal" data-target="#revocation-modal" data-dist-name="'+e.name+'" data-dist-id="'+e.id+'">'+t+"</a>"};return console.log(e.revocation_state),"pending"==e.revocation_state?'<span class="text-warning">审核中</span>':"revocated"==e.revocation_state?'<span class="text-success">已取消授权</span>':"rejected"==e.revocation_state?'<span class="text-danger">审核失败;</span>'+t("点击再次提交审核"):t("取消授权")}}]}),e("#distributors").delegate('[data-target="#revocation-modal"]',"click",function(){var t=e(this).data("dist-id"),a=e(this).data("dist-name"),s=e("#contract-form"),i=s.attr("action").split("/");i[3]=t,e("#modal-dist-name").text(a),e("#contract").val(""),s.attr("action",i.join("/"))})}if("dist-invitation"===getPageTitle()&&e("#get-key").click(function(){var t=e(this);if(!t.hasClass("disabled")){var a=t.text();setButtonLoading(t),e.ajax({url:"/vendor/distributors/invitation",method:"post",success:function(s){e(".invite-key").val(s).attr("contenteditable",!0).focus().select(),resetButton(t,a)},error:function(e){toastr.error("服务器"+e.status+"错误.","申请失败!"),resetButton(t,a)}})}}),"settings"===getPageTitle()&&(e("#logo").on("change",function(){var t=e(this),a=this.files?this.files:[];if(!(a.length<=0)&&window.FileReader&&/^image/.test(a[0].type)){var s=new FileReader;s.readAsDataURL(a[0]),s.onloadend=function(){t.siblings(".logo-preview").find("img").attr("src",this.result)}}}),e("#mobile").rules("add",{mobile:!0,messages:{mobile:"请填写合法的手机号码"}}),e("#telephone").rules("add",{tel:!0,messages:{tel:"请填写合法的固定电话号码"}}),e("#send-email").click(function(){var t=e(this).data("vendor-id");e.ajax({url:"/service/send_email?type=VENDOR_EMAIL_CONFIRM",method:"post",data:{csrf_token:e("#csrf_token").val(),role:"vendor",id:t},success:function(e){e.success?toastr.success("验证邮件已发送, 请查收","发送成功!"):toastr.error(e.message,"发送失败!")},error:function(e){toastr.error("服务器"+e.status+"错误...","发送失败!")}})})),"register"==e("body").data("page")){var g=e(".send"),f=6e4,v=g.val()||g.text();getCookie("clickTime")&&(sendDisable(g,Date.now(),f),setCountDown(g,v,f)),g.click(function(){if(checkValidate(e("#register"),"#mobile")){var t=e(this);t.hasClass("disabled")||(setCookie("clickTime",Date.now()),e.ajax({url:"/service/mobile_register_sms",method:"post",data:{mobile:e("#mobile").val()}}),setCountDown(t,v,f))}})}("register-next"==e("body").data("page")||"reconfirm"==e("body").data("page"))&&("register-next"==e("body").data("page")&&(e("#email").rules("add",{required:!0,email:!0,messages:{required:"请输入您的邮箱",email:"请输入合法的邮箱地址"}}),e("#password").rules("add",{required:!0,password:!0,messages:{required:"请设置密码",password:"密码长度必须大于等于6位且为字母和数字的组合"}}),e("#confirm_password").rules("add",{required:!0,equalTo:"#password",messages:{required:"请再次输入密码",equalTo:"两次密码输入不一致"}}),e("#agent_identity_front").rules("add",{required:!0,messages:{required:"请上传代理人身份证正面照片"}}),e("#agent_identity_back").rules("add",{required:!0,messages:{required:"请上传代理人身份证反面照片"}}),e("#license_image").rules("add",{required:!0,messages:{required:"请上传营业执照照片"}})),e("#agent_name").rules("add",{required:!0,messages:{required:"请输入代理人姓名"}}),e("#agent_identity").rules("add",{required:!0,identity:!0,messages:{required:"请输入代理人身份证",identity:"不合法的身份证号码"}}),e("#name").rules("add",{required:!0,messages:{required:"请填写厂家名称"}}),e("#license_limit").rules("add",{required:!0,customDate:!0,messages:{required:"请填写营业期限",customDate:"不合法的日期格式, 格式: 2015/07/19"}}),e("#telephone").rules("add",{required:!0,tel:!0,messages:{required:"请填写联系固话",tel:"不合法的电话号码"}}),e("#province_cn_id").rules("add",{required:!0,messages:{required:"请选择省级行政区"}}),e("#city_cn_id").rules("add",{required:!0,messages:{required:"请选择市级行政区"}}),e("#district_cn_id").rules("add",{required:!0,messages:{required:"请选择区级行政区"}}),e("#address").rules("add",{required:!0,messages:{required:"请填写联系地址"}}))});