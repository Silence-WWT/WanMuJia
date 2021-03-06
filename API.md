# WanMuJia API Doc
## User
### user register
+ **URL**
  + /register
+ **method**
  + GET
  + POST
+ step == 1
  + **postData**
    + **csrf_token**
    + **mobile**
      + 手机号码
      + type = text
      + length = 11
      + require
    + **captcha**
      + 短信验证码
      + type = text
      + length = 6
      + require
  + **return**
    + 成功
      + `{"success": true}`
    + 失败
      + `{"success": false, "message": ""}`
+ step == 2
  + **postData**
    + **csrf_token**
    + **password**
      + 密码
      + type = password
      + length = [6, 32]
      + require
      + 需将用户的密码md5两次
    + **confirm_password**
      + 确认密码
      + type = password
      + length = [6, 32]
      + require
      + 需将用户的密码md5两次, 且与password相等
  + **return**
    + 成功
      + `{"status": true, "user": {"username": "", "mobile": ""}}`
    + 失败
      + `{"status": false, "message": ""}`

### user login
+ **URL**
  + /login
+ **method**
  + GET
  + POST
+ **postData**
  + **csrf_token**
  + **username**
    + 用户名 (手机号码 或 邮箱)
    + type = text
    + require
  + **password**
	+ 密码
    + type = password
    + require
    + 需将用户密码md5两次
  + **remember**
    + 记住密码
    + type = bool
+ **return**
  + 成功
    + `{"status": true, "user": {"username": "", "mobile": "", "email": ""}}`
  + 失败
    + `{"status": false, "message": ""}`
    
### user logout
+ **URL**
  + /logout
+ **method**
  + GET

### user reset password
+ **URL**
  + /reset_password
+ **method**
  + GET
  + POST
+ step == 1
  + **postData**
    + **csrf_token**
    + **mobile**
      + 手机号码
      + type = text
      + length = 11
      + require
    + **captcha**
      + 短信验证码
      + type = text
      + length = 6
      + require
  + **return**
    + 成功
      + `{"success": true}`
    + 失败
      + `{"success": false, "message": ""}`
+ step == 2
  + **postData**
    + **csrf_token**
    + **password**
      + 密码
      + type = password
      + length = [6, 32]
      + require
      + 需将用户的密码md5两次
    + **confirm_password**
      + 确认密码
      + type = password
      + length = [6, 32]
      + require
      + 需将用户的密码md5两次, 且与password相等
  + **return**
    + 成功
      + `{"status": true, "user": {"username": "", "mobile": ""}}`
    + 失败
      + `{"status": false, "message": ""}`

### user home page
+ **URL**
  + /profile
+ **method**
  + GET

### user collection
+ **URL**
  + /collection
+ **method**
  + GET
  + POST
  + DELETE
+ **parameters**
  + page
    + 页数, 从1开始, 仅GET方式需要
  + item: item id, 仅POST, DELETE方式需要
+ **return**
  + GET
    + `{"collections": [{"item": "", "price": "", "item_id": "", "deleted": "", "image_url": "", "is_suite": ""}], "amount": "", "page": "", "pages": ""}`
    + **amount**
      + 收藏总数
    + **page**
      + 当前页数
    + **pages**
      + 总页数
  + POST
    + `{"success": false, "message": "该商品不存在"}`
    + `{"success": true}`
  + DELETE
    + `{"success": true}`

### user change username
+ **URL**
  + /settings
+ **method**
  + POST
+ **parameters**
  + type = USER_USERNAME_SETTING
+ **postData**
  + captcha
  + username
+ **return**
  + 成功
    + `{"success": true}`
  + 失败
    + `{"success": false, "message": ""}`

### user change email
+ **URL**
  + /settings
+ **method**
  + POST
+ **parameters**
  + type = USER_EMAIL_SETTING
+ **postData**
  + captcha
  + email
+ **return**
  + 成功
    + `{"success": true}`
  + 失败
    + `{"success": false, "message": ""}`

### user change password
+ **URL**
  + /settings
+ **method**
  + POST
+ **parameters**
  + type = USER_PASSWORD_SETTING
+ **postData**
  + old_password
  + password
  + confirm_password
+ **return**
  + 成功
    + `{"success": true}`
  + 失败
    + `{"success": false, "message": ""}`

### user logined
+ **URL**
  + /logined
+ **method**
  + GET
+ **return**
  + 已登录
    + `{"logined": true, "username": "", "mobile": "", "email": "", "username_revisable": "", "email_confirmed": ""}`
  + 未登录
    + `{"logined": false}`

## Main
### index
+ **URL**
  + /
+ **method**
  + GET

### index navbar
+ **URL**
  + /navbar
+ **method**
  + GET
+ **return**
  + items列表长度正常情况下为8 (但是有可能商品数量确实不够的情况...)
```json
{
    "id1": {
        "scene": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    },
    "id2": {
        "scene": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    },
    "id3": {
        "scene": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    }
}
```

### brand list
+ **URL**
  + /brands
+ **method**
  + GET
+ **parameters**
  + format
    + 若format != json, 返回html(brands.html)
    + 若format == json, 返回json
+ **return**
```json
{
    "id1": {
        "brand": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    },
    "id2": {
        "brand": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    }
}
```

### brand detail
+ **URL**
  + /brands/\<int:brand_id\>
+ **method**
  + GET
+ **parameters**
  + format
    + 若format != json, 返回html(brand_detail.html)
    + 若format == json, 返回json
+ **return**
```json
{
    "id1": {
        "scene": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    },
    "id2": {
        "scene": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    }
}
```

### furniture
+ **URL**
  + /furniture
+ **method**
  + GET
+ **parameters**
  + format
    + 若format != json, 返回html(furniture.html)
    + 若format == json, 返回json
+ **return**
```json
{
    "id1": {
        "style": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    },
    "id2": {
        "style": "",
        "items": [
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": true},
            {"id": "", "item": "", "price": "", "image_url": "", "is_suite": false}
        ]
    }
}
```

### feedback
+ **URL**
  + /feedback
+ **method**
  + POST
+ **postData**
  + csrf_token
  + feedback
  + contact
+ **return**
  + `{"success": true}`
  + `{"success": false, "message": ""}`

## Item
### item list
+ **URL**
  + /item
+ **method**
  + GET

### item filter
+ **URL**
  +	/item/filter
+ **method**
  + GET
+ **parameters**
  +	page
    + 从1开始
  +	brand
  + material
  + style
  + scene
  + category
  + search
    + 搜索关键字
  + price
    + 价格 index(6个选项的索引值)
    + value = [0, 5]
  + order
    + 按照价格排序
    + value = "desc" or "asc"
+ **return**
  + filters
    + available
      + 可选条件
      + brand
        + id
        + brand
      + category
        + id
        + category
      + material
        + id
        + material
      + scene
        + id
        + scene
      + style
        + id
        + style
      + price
        + id
        + price
    + selected
      + 已选条件
      + 结构与available相同, 单个筛选条件(除category)只会在available或selected其中之一出现
      + category为分级筛选, 选择第一级条件后, 会返回第二级条件
  + items
    + amount
      + 符合条件的所有商品数量
    + page
      + 当前页数(从1开始)
    + pages
      + 过滤结果总共页数
    + search
      + 搜索关键词
    + order
      + 排序方式(按照价格)
      + value = "asc" or "desc" or null(未排序)
    + query
      + id
      + item
      + price
      + image_url
      + is_suite

```json
{
	"filters": {
		"available": {
			"brand": {
				"id1": {"brand": ""},
				"id2": {"brand": ""}
			},
			"category": {
				"id1": {"category": ""},
				"id2": {"category": ""}
			},
			"material": {
				"id1": {"material": ""},
				"id2": {"material": ""}
			},
			"scene": {
				"id1": {"scene": ""},
				"id2": {"scene": ""}
			},
			"style": {
				"id1": {"style": ""},
				"id2": {"sty;e": ""}
			},
			"price": {
				"price1": {"price": ""},
				"price2": {"price": ""}
			}
		},
		"selected": {
		    "category": {
		        "id": {
		            "category": "",
		            "children": {
		                "id": {
		                    "category": ""
		                }
		            }
		        }
		    }
		}
	},
	"items": {
		"amount": "",
		"page": "",
		"pages": "",
		"search": "",
		"order": "",
		"query": [
			{"id": "", "item": "", "price": "", "image_url": "", "is_suite": false},
			{"id": "", "item": "", "price": "", "image_url": "", "is_suite": true}
		]
	}
}
```

### item compare
+ **URL**
  + /item/compare
+ **method**
  + GET

### item detail
+ **URL**
  + /item/\<int: id\>
+ **method**
  + GET
+ **parameters**
  + format
    + 若format != json, 返回html
    + 若format == json && action == detail, 返回商品详情
    + 若format == json && action != detail, 返回商品对比详情
+ **return**
  + format == json && action != detail
    + `{"id": "", "item": "", "price": "", "second_material": "", "category": "", "second_scene": "", "outside_sand": "", "inside_sand": "", "size": "", "area": "", "stove": "", "carve_type": "", "carve": [""], "tenon": [""], "paint": "", "decoration": "", "story": "", "image_url": "", "brand": ""}`
    + **id**
      + 商品id
    + **item**
      + 商品名称
    + **price**
      + 指导价格
    + **second_material**
      + 二级材料
    + **category**
      + 商品分类
    + **scene**
      + 二级场景分类
    + **outside_sand**
      + 外表面打磨砂纸
    + **inside_sand**
      + 内表面打磨砂纸
    + **size**
      + 长 * 宽 * 高
    + **area**
      + 适用面积
    + **stove**
      + 烘干工艺
    + **paint**
      + 涂饰工艺
    + **decoration**
      + 装饰工艺
    + **carve**
      + 雕刻工艺
    + **carve_type**
      + 雕刻方式
    + **tenon**
      + 榫卯结构
    + **story**
      + 商品寓意
    + **image_url**
      + 图片url
    + **brand**
      + 品牌
    + **is_suite**
      + value = False
  + format == json && action == detail
    + item object(**单件**)
      + id
      + vendor_id
        厂家 id
      + brand
        + 品牌名
      + item
        + 商品名
      + price
        + 指导价格
      + size
        + 长 * 宽 * 高
      + area
        + 适用面积
      + second_material
        + 材料
      + category
        + 分类
      + scene
        + 场景
      + stove
        + 烘干工艺
      + outside_sand
        + 外表面打磨砂纸
      + inside_sand
        + 内表面打磨砂纸
      + paint
        + 涂饰工艺
      + decoration
        + 装饰工艺
      + style
        + 风格
      + images
        + 商品图片
      + is_suite
        + value = False
      + is_component
        + value = False
    + item object(**套件**)
      + id
      + vendor_id
        + 厂家id
      + brand
        + 商品品牌
      + item
        + 商品名称
      + area
        + 适用面积
      + price
        + 指导价格
      + second_material
        + 材料
      + scene
        + 场景
      + style
        + 风格
      + outside_sand
        + 外表面砂纸
      + inside_sand
        + 内表面砂纸
      + stove
        + 烘干工艺
      + amount
        + 该套件中所有组件数量和
      + images
        + 套件图片
      + components
        + 套件中的组件
      + is_suite
        + value = True
    + item object(**组件**)
      + item
        + 组件名称
      + size
        + 长 * 宽 * 高
      + area
        + 适用面积
      + category
        + 组件分类
      + carve
        + 雕刻工艺
      + tenon
        + 榫卯结构
      + paint
        + 涂饰工艺
      + decoration
        + 装饰工艺
      + amount
        + 该组件的数量
      + is_component
        + value = True

```js
{
    "item": {
        "collected": "",  // true or false

        // 单件
        "id": "",
        "item": "",
        "vendor_id": "",
        "brand": "",
        "price": "",
        "second_material": "",
        "category": "",
        "scene": "",
        "style": "",
        "outside_sand": "",
        "inside_sand": "",
        "size": "",
        "area": "",
        "stove": "",
        "paint": "",
        "decoration": "",
        "carve": ["", ""],
        "carve_type": "",
        "tenon": ["", ""],  // 榫卯结构为选填, 可能为[]
        "images": ["", ""],
        "is_suite": false,
        
        // 套件
        "id": "",
        "item": "",
        "vendor_id": "",
        "brand": "",
        "price": "",
        "second_material": "",
        "scene": "",
        "style": "",
        "outside_sand": "",
        "inside_sand": "",
        "area": "",
        "stove": "",
        "carve_type": "",
        "amount": "",
        "images": ["", ""],
        "is_suite": true,
        "components": [
            {
                "item": "",
                "category": "",
                "area": "",
                "size": "",
                "paint": "",
                "decoration": "",
                "carve": ["", ""],
                "tenon": ["", ""],  // 榫卯结构为选填, 可能为[]
                "amount": "",
                "is_component": true
            },
        ]
    },
    "distributors": {
        "id1": {
            "area": "",
            "children": {
                "id2": {
                    "area": "",
                    "children": {
                        "id3": {
                            "area": "",
                            "distributors": {
                                "id5": {
                                    "name": "xxx体验馆",
                                    "ext_number": ""
                                },
                                "id6": {
                                    "name": "xxx体验馆",
                                    "ext_number": ""
                                },
                            }
                        }
                    }
                }
            }
        }
    }
}
```

## Distributor
### distributor register
+ **URL**
  + /distributor/register
+ **method**
  + GET
  + POST
+ **postData**
  + **name** 
    + 商家名称
    + type = text
    + required
  + **password**
    + 密码
    + type = password
    + required
  + **confirmed_password**
    + 确认密码
    + type = password
    + required
  + **contact**
    + 联系人姓名
    + type = text
    + required
  + **contact_mobile**
    + 联系人手机
    + type = text
    + required
  + **contact_telephone**
    + 固话
    + type = text
    + required
  + **district_cn_id**
    + 行政区号
    + select
    + required
  + **address**
    + 详细地址
    + type = text
    + required

        
## Vendor
### vendor register
+ **URL**
  + /vendor/register
+ **method**
  + GET, POST
+ **postData**
  + **password**
    + 密码
    + type = text
    + required 
  + **confirm_password**
    + 确认密码
    + type = text
    + required
  + **email**
    + 邮箱
    + type = text
    + required
  + **agent_name**
    + 代理人姓名
    + type = text
    + required
  + **agent_identity**
    + 代理人身份证号
    + type = text
    + required
  + **agent_identity_front**
    + 代理人身份证正面照片
    + type = img
    + required
  + **agent_identity_back**
    + 代理人身份证反面照片
    + type = img
    + required
  + **name**
    + 厂家名称
    + type = text
    + required
  + **license_limit**
    + 营业执照期限
    + type = text
    + required
  + **license_image**
    + 营业执照照片
    + type = img
    + required
  + **telephone**
    + 固话
    + type = text
    + required
  + **address**
    + 详细地址
    + type = text
    + required
  + **district_cn_id**
    + 区域的cn_id
    + type = text
    + required

### vendor login
+ **URL**
  + /vendor/login
+ **method**
  + GET
  + POST
+ **postData**
  + **mobile**
    + 手机号码
    + type = text
    + required
  + **password**
    + 密码
    + type = text
    + required
    + 需要md5两次

### vendor logout
+ **URL**
  + /vendor/logout
+ **method**
  + GET

### vendor reset password
+ **URL**
  + /vendor/reset_password
+ **method**
  + GET
  + POST
  
### vendor index
+ **URL**
  + /vendor
+ **method**
  + GET
  
### vendor item page
+ **URL**
  + /vendor/items
+ **method**
  + GET

### vendor items datatable
+ **URL**
  + /vendor/items?draw=&start=&length=
+ **method**
  + GET
+ **paramaters**
  + draw
  + start
  + length

### vendor add single item
+ **URL**
  + /vendor/items/new_item?type=single
+ **method**
  + GET, POST
+ **postData**
  + **item**
    + 商品名称
    + type = text
    + required
  + **length**
    + 商品长度
    + type = text
    + 商品长宽高与适用面积二选其一
    + 商品长宽高只能全部填写或全不填写
  + **width**
    + 商品宽度
    + type = text
  + **heigth**
    + 商品高度
    + type = text
  + **area**
    + 商品适用面积
    + type = text
    + 商品适用面积与长宽高二选其一
  + **price**
    + 商品指导价格
    + type = text
    + required
  + **second_material_id**
    + 商品二级材料id
    + type = text
    + required
  + **category_id**
    + 商品分类id
    + type = text
    + required
  + **stove_id**
    + 烘干工艺id
    + type = text
    + required
  + **carve_id**
    + 雕刻工艺id
    + type = text
    + required
  + **carve_type_id**
    + 雕刻方式id
    + type = text
    + requid
  + **outside_sand_id**
    + 外表面打磨砂纸id
    + type = text
    + required
  + **inside_sand_id**
    + 内表面打磨砂纸id
    + type = text
  + **paint_id**
    + 涂饰工艺id
    + type = text
    + required
  + **decoration_id**
    + 装饰工艺id
    + type = text
    + required
  + **tenon_id**
    + 榫卯结构id
    + type = text
    + required
  + **story**
    + 商品寓意
    + type = text

### vendor add suite
+ **URL**
  + /vendor/items/new_item?type=suite
+ **method**
  + POST
+ **postData**
  + **item**
    + 套件名称
    + type = text
    + required
  + **area**
    + 商品适用面积
    + type = text
  + **price**
    + 商品指导价格
    + type = text
    + required
  + **second_material_id**
    + 商品二级材料id
    + type = text
    + required
  + **category_id**
    + 商品分类id
    + type = text
    + required
  + **scene_id**
    + 二级场景id
    + type = text
    + required
  + **stove_id**
    + 烘干工艺id
    + type = text
    + required
  + **carve_id**
    + 雕刻工艺id
    + type = text
    + required
  + **carve_type_id**
    + 雕刻方式id
    + type = text
    + required
  + **outside_sand_id**
    + 外表面打磨砂纸id
    + type = text
    + required
  + **inside_sand_id**
    + 内表面打磨砂纸id
    + type = text
  + **story**
    + 商品寓意
    + type = text
  + **components**
    + 包含组件信息列表的字符串
    + "{'components': ['component': '', 'length': '', 'width': '', 'height': '', 'area': '', 'category_id': '', 'carve_id': '', 'paint_id': '', 'decoration_id':　'', 'tenon_id': '', 'amount': '']}"
    + required
    + **component**
      + 组件名称
      + type = text
      + required
    + **length**
      + 组件长度
      + type = text
      + 组件长宽高与适用面积二选其一
      + 组件长宽高只能全部填写或全不填写
    + **width**
      + 组件宽度
      + type = text
    + **height**
      + 组件高度
      + type = text
    + **area**
      + 组件适用面积
      + type = text
      + 组件适用面积与长宽高二选其一
    + **category_id**
      + 组件种类id
      + type = text
      + required
    + **carve_id**
      + 雕刻id
      + type = text
      + required
    + **decoration_id**
      + 装饰工艺id
      + type = text
      + required
    + **tenon_id**
      + 榫卯结构id
      + type = text
      + required
    + **amount**
      + 组件数量
      + type = text
      + required

### vendor item detail
+ **URL**
  + /vendor/items?item=
+ **method**
  + GET
+ **parameters**
  + item: item id

### vendor edit item
+ **URL**
  + /vendor/items/\<int:id\>
+ **method**
  + PUT
+ **parameters**
  + : item id

### vendor delete item
+ **URL**
  + /vendor/items?item=
+ **method**
  + DELETE
+ **parameters**
  + item: item id
  + Item Form
	+ item: 
	  + 商品名称
	  +  require
	  + length: [1, 20]
	+ length
	  + 商品长度(cm)
	  + require
	+ width
	  + 商品宽度(cm)
	  + require
	+ height
	  + 商品高度(cm)
	  + require
	+ price
	  + 指导价格(元)
	  + require
	+ material_id
	  + 二级材料id
	  + require
	+ second_category_id
      + 二级分类id
	  + require
	+ stove_id	
	  + 烘干工艺id
	  + require
	+ carve_id
	  + 雕刻工艺id
	  + require
	+ sand_id
	  + 打磨砂纸id
	  + require
	+ paint_id
	  + 涂饰工艺id
	  + require
	+ decoration_id
	  + 装饰工艺id
	  + require
	+ tenon_id
	  + 榫卯结构id
	  + require
	+ story
	  + 商品寓意
	  + length: [0, 5000]

### vendor oss signature
+ **URL**
  + /vendor/items/oss_signature
+ **method**
  + GET
+ **parameters**
  + item_id
  + filename
+ **return**
  + 成功
    + `{"success": true, "url": "", "params": {"key": "", "OSSAccessKeyId": "", "Signature": "", "callback": "", "policy": ""}`
    + url
      + ajax请求的url. 请求此url成功上传后, OSS会回调万木家的接口, 并将万木家返回的信息返回给前端
    + params
      + 需要设置的表单域name与value
  + 失败
    + `{"success": false}`

### vendor item image
+ **URL**
  + `vendor oss signature`返回的url
  + /vendor/items/image
+ **method**
  + PUT
  + DELETE
+ PUT image
  + **postData**
    + 图片
  + **return**
    + `{"success": true, "image": {"url": "", "hash": "", "created": ""}}`
+ DELETE image
  + **postData**
    + image_hash
  + **return**
    + 成功
      + {"success": true}
    + 失败
      + {"success": false}

### vendor distributors
+ **URL**
  + /vendor/distributors
+ **method**
  + GET

### vendor distributor detail
+ **URL**
  + /vendor/distributors/\<distributor_id\>
+ **method**
  + GET

### vendor distributor invitation
+ **URL**
  + /vendor/distributors/invitation
+ **method**
  + GET, POST

### vendor distributors revocation
+ **URL**
  + /distributors/\<int:distributor_id\>/revocation
+ **method**
  + POST
    
### vendor settings
+ **URL**
  + /vendor/settings
+ **method**
  + GET
  + POST

### vendor reconfirm
+ **URL**
  + /vendor/reconfirm
+ **method**
  + GET
  + POST


## privilege

### login
+ **URL**
  + /privilege/login
+ **method**
  + GET, POST
+ **postData**
  + username
  + password
    
### vendor_confirm
+ **URL**
  + /privilege/vendor_confirm
+ **method**
  + GET
    
### vendor_confirm reject
+ **URL**
  + /privilege/vendor_confirm/reject
+ **method**
  + POST
+ **postData**
  + vendor_id
  + reject_message
    
### vendor_confirm pass
+ **URL**
  + /privilege/vendor_confirm/pass
+ **method**
  + POST
+ **postData**
  + vendor_id
    
### distributors revocation
+ **URL**
  + /privilege/distributors/revocation
+ **method**
  + GET
  + POST
+ **postData**
  + distributor_revocation_id
  + revocation_confirm

## Operation
### login
+ **URL**
  + /operation/login
+ **method**
  + GET
  + POST
+ **postData**
  + csrf_token
  + username
  + password

### index
+ **URL**
  + /operation/
+ **method**
  + GET
+ **template data**
  + records
  + pages
```js
records = [
    {
        "item": "",
        "brand": "",
        "distributor": "",
        "distributor_address": "",
        "distributor_telephone": "",
        "distributor_mobile": "",
        "mobile": "",
        "created": "",
        "item_url": ""
    }
]
```

## Service
### mobile register sms
+ **URL**
  + /service/mobile_register_sms
+ **method**
  + POST
+ **postData**
  + mobile
+ **return**
  + 成功
    + `{"success": true}`
  + 失败
    + `{"success": false, "message": ""}`
    
### mobile sms
+ **URL**
  + /service/mobile_sms
+ **method**
  + POST
+ **parametes**
  + type
    + USER_RESET_PASSWORD
    + USER_GUIDE
+ **postData**
  + type == USER_RESET_PASSWORD
    + **csrf_token**
    + **mobile**
      + required
  + type == USER_GUIDE
    + **csrf_token**
    + **item_id**
      + required
    + **distributor_id**
      + required
    + **mobile**
      + required
    + **captcha**
      + required

### mobile sms login required
+ **URL**
  + /service/mobile_sms_login_required
+ **method**
  + POST
+ **parameters**
  + type
    + USER_SMS_CAPTCHA(适用于用户修改用户名/密码/email)
+ **postData**
  + type == USER_SMS_CAPTCHA
    + **csrf_token**
      + required
    + **mobile**
      + required

### send email
+ **URL**
  + /service/send_email
+ **method**
  + POST
+ **parameters**
  + **type**(以下之一)
    + USER_REGISTER
    + USER_EMAIL_CONFIRM
    + USER_RESET_PASSWORD
    + VENDOR_EMAIL_CONFIRM
+ **postData**
  + USER_REGISTER
    + **csrf_token**
    + **email**
      + 用户邮箱
      + require
  + USER_EMAIL_CONFIRM
    + **csrf_token**
    + **role**
      + 身份
      + value = user
    + **id**
      + 用户id
  + USER_RESET_PASSWORD
    + **csrf_token**
    + **email**
      + required
  + VENDOR_EMAIL_CONFIRM
    + **csrf_token**
    + **role**
      + 身份
      + value = vendor
    + **id**  
      + 用户id
      + require
+ **return**
  + 成功
    + ```{"success": true}```
  + 失败
    + `{"success": false, "message": ""}`
    
### image captcha
+ **URL**
  + /service/\<string:token\>.jpg
+ **method**
  + GET
+ **return**
  + img
  
### cities list
+ **URL**
  + /service/cities
+ **mehtod**
  + GET
+ **return**
  + json
  + `{"A": {"ankang": {"city": "安康", "dist_count": "5"}}}`

### client ip
+ **URL**
  + /service/client_ip
+ **method**
  + GET
+ **return**
  + `{"ip": ""}`
