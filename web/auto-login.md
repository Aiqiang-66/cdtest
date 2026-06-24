# Web 鑷姩鐧诲綍涓?Token 鎻愬彇

## 瀹氫綅

**鍦?Phase 0 鐜妫€鏌ュ悗绔嬪嵆鎵ц銆備娇鐢?agent-browser 瀹屾垚鑷姩鐧诲綍 + Token 鎻愬彇銆傝繖鏄幏鍙栨巿鏉冪殑鍞竴鏍囧噯璺緞銆?*

> **Token 鎻愬彇浼樺厛绾ч摼锛圵eb 鍞竴鏉冨▉鏉ユ簮锛?*:
> 鏈枃浠跺畾涔夌殑 5 绾т紭鍏堢骇閾撅紙localStorage > Cookies > JS鍙橀噺 > 宸茬煡API > 閰嶇疆鏂囦欢锛?> 鏄?Web 骞冲彴鐨勫敮涓€鏉冨▉鏉ユ簮銆俰OS/Android 骞冲彴鏈夊悇鑷嫭绔嬬殑 Token 鎻愬彇閾撅紙瑙佸悇骞冲彴 session.md锛夛紝
> 鍥犲钩鍙板樊寮傦紙鏃犳硶璁块棶 localStorage锛夛紝浼樺厛绾ч摼鍐呭涓嶅悓灞炰簬璁捐棰勬湡锛岄潪涓嶄竴鑷寸己闄枫€?
---

## 涓€銆佹墽琛屽墠缃?
```yaml
鍓嶇疆鏉′欢:
  1. agent-browser 宸插畨瑁? agent-browser --version
  2. 娴嬭瘯 URL / 鐧诲綍鍑瘉宸蹭粠 spec/ 鎴栫敤鎴疯緭鍏ヤ腑鎻愬彇
  3. 濡?agent-browser 涓嶅彲鐢?鈫?鎻愮ず鐢ㄦ埛瀹夎: npm install -g agent-browser
```

---

## 浜屻€佽嚜鍔ㄧ櫥褰曟祦绋嬶紙鍥哄畾 4 姝?+ AI 璇嗗埆锛?
```yaml
# 杩欐槸 cdtest 鑾峰彇鎺堟潈鐨勫敮涓€鏍囧噯璺緞銆傜姝㈣烦杩?agent-browser 鐩存帴鐢?curl 鐚滄祴 API 鐧诲綍銆?
姝ラ 1: 鎵撳紑椤甸潰锛堟渶澶у寲绐楀彛锛?  鍛戒护:
    agent-browser open "{娴嬭瘯URL}" --headed --args "--start-maximized,--disable-password-manager,--disable-password-manager-reauthentication,--disable-save-password-bubble,--disable-password-leak-detection"
  
  绛夊緟椤甸潰鍔犺浇瀹屾垚鍚庨獙璇?
    agent-browser eval "window.innerWidth + 'x' + window.innerHeight"
    鈫?棰勬湡瀹藉害>=1920锛屽鏋滀笉鏄垯绐楀彛鏈渶澶у寲锛岄噸鏂拌缃?
姝ラ 2: 璇嗗埆鐧诲綍椤甸潰绫诲瀷锛坰napshot锛?  鍛戒护:
    agent-browser snapshot
  
  绫诲瀷鍖归厤:
    - 椤甸潰鏈?"宸ュ彿鐧诲綍" 鍏ュ彛 鈫?绫诲瀷C1: 宸ュ彿鐧诲綍锛堝鍏ュ彛锛?    - 椤甸潰鏈?input[type=text] + input[type=password] + 鐧诲綍鎸夐挳 鈫?绫诲瀷A: 鏍囧噯琛ㄥ崟
    - 椤甸潰璺宠浆鍒?sso.xxx.com 鈫?绫诲瀷B: SSO
    - 椤甸潰鏈夐獙璇佺爜 鈫?绫诲瀷D: 楠岃瘉鐮侊紙璁板綍璺宠繃锛屾彁绀轰汉宸ワ級
    - 椤甸潰宸叉湁鐢ㄦ埛鑿滃崟 鈫?绫诲瀷E: 宸茬櫥褰曪紙璺冲埌姝ラ3锛?
姝ラ 3: 鎵ц鐧诲綍

  # 绫诲瀷C1: 宸ュ彿鐧诲綍锛堟渶甯歌鐨勪紒涓氬唴閮ㄧ郴缁熺櫥褰曟柟寮忥級
  鐗瑰緛: 鐧诲綍椤垫湁鍒嗘鎺т欢锛屽寘鍚?宸ュ彿鐧诲綍"+"閽夐拤鐧诲綍"/"璐﹀彿鐧诲綍"绛夊涓叆鍙?  绛栫暐:
    1. snapshot 鈫?鎼滅储"宸ュ彿鐧诲綍" 鈫?鎵惧埌鍏?LabelText ref 鈫?agent-browser click {ref}
    2. snapshot 纭鍒囨崲鍒板伐鍙风櫥褰曡〃鍗曪紙鍑虹幇"鐢ㄦ埛鍚?/"瀵嗙爜"杈撳叆妗嗭級
    3. fill "鐢ㄦ埛鍚?杈撳叆妗?鈫?杈撳叆宸ュ彿
    4. fill "瀵嗙爜"杈撳叆妗?鈫?杈撳叆瀵嗙爜
    5. click "鐧诲綍"鎸夐挳
    6. 绛夊緟椤甸潰璺宠浆锛堟渶闀?10 绉掞級
    7. snapshot 纭宸茬櫥褰曪紙妫€鏌ュ鑸彍鍗?鐢ㄦ埛淇℃伅绛夊厓绱狅級

  # 绫诲瀷C2: 璐﹀彿鐧诲綍锛堝鍏ュ彛涓殑鏅€氳处鍙风櫥褰曪級
  鐗瑰緛: 鏈?璐﹀彿鐧诲綍"+"鎵爜鐧诲綍"绛夊涓叆鍙?  绛栫暐:
    1. click "璐﹀彿鐧诲綍"鍏ュ彛
    2. fill 鐢ㄦ埛鍚?+ 瀵嗙爜 + click 鐧诲綍锛堝悓绫诲瀷A锛?
  # 绫诲瀷A: 鏍囧噯琛ㄥ崟
  鐗瑰緛: 鐩存帴鏄剧ず input[type=text] + input[type=password] + 鐧诲綍鎸夐挳
  绛栫暐:
    1. fill 鐢ㄦ埛鍚嶈緭鍏ユ
    2. fill 瀵嗙爜杈撳叆妗?    3. click 鐧诲綍鎸夐挳
    4. 绛夊緟椤甸潰璺宠浆
    5. snapshot 纭宸茬櫥褰?
  # 绫诲瀷B: SSO/OAuth
  鐗瑰緛: 鍩熷悕璺宠浆鍒扮涓夋柟鐧诲綍椤?  绛栫暐:
    1. 璺熼殢璺宠浆
    2. 璇嗗埆鐩爣鐧诲綍椤电被鍨嬶紝鎸夊搴旂瓥鐣ュ鐞?    3. 绛夊緟璺宠浆鍥炲師鍩熷悕
    4. snapshot 纭宸茬櫥褰?
姝ラ 4: 鎻愬彇 Token锛堝浐瀹氫紭鍏堢骇閾撅級
  鎸変互涓嬮『搴忓皾璇曪紝浠讳竴姝ユ垚鍔熷嵆鍋滄:

  浼樺厛绾?1: localStorage锛圫PA 鏈€甯歌锛岄閫夛級
    agent-browser eval "Object.keys(localStorage).filter(k => /token|auth|jwt|session/i.test(k)).map(k => k + ': ' + localStorage.getItem(k).substring(0, 80)).join(' | ')"
    鈫?鎵惧埌鍖呭惈 token 鐨?key 鈫?鑾峰彇瀹屾暣鍊?
    agent-browser eval "localStorage.getItem('token')"
    鈫?楠岃瘉: 鐢ㄦ Token 璋冧换鎰忓凡鐭?API锛岃繑鍥?200 鍗虫湁鏁?
  浼樺厛绾?2: Cookies
    agent-browser eval "document.cookie.split(';').filter(c => /token|auth|jwt|session/i.test(c))"
    鈫?鎻愬彇鍖归厤鐨?cookie 鍊?鈫?楠岃瘉

  浼樺厛绾?3: JS 鍙橀噺
    agent-browser eval "window.__INITIAL_STATE__?.auth?.token || window.__NUXT__?.state?.auth?.token || window.__NEXT_DATA__?.props?.pageProps?.token"
    鈫?鍙栫涓€涓潪绌哄€?鈫?楠岃瘉

  # 鈿狅笍 浼樺厛绾?4 浠呭湪浠ヤ笅鏉′欢鍏ㄩ儴婊¤冻鏃舵墽琛?
  #   1. 宸茬煡鏄庣‘鐨勭櫥褰?API 绔偣
  #   2. 绔偣鏉ヨ嚜 Swagger 鏂囨。鎴?spec/ 閰嶇疆锛堥潪鐚滄祴锛?  #   3. 鍓?3 涓紭鍏堢骇鍧囧け璐?  浼樺厛绾?4: 宸茬煡 API 鐧诲綍锛堥渶鏈夋槑纭鐐癸級
    鍓嶆彁: swagger.json 鎴?spec/ 涓凡璁板綍鐧诲綍 API 绔偣
    POST {api_base}/{宸茬煡鐧诲綍璺緞}
    鈫?鎻愬彇 token 鈫?楠岃瘉
    鉀?濡傛灉娌℃湁鏄庣‘绔偣锛岀珛鍗宠烦杩囨姝ラ锛屼笉瑕佺寽娴嬶紒

  浼樺厛绾?5: 閰嶇疆鏂囦欢
    spec/config.yaml 鎴?.env 涓殑 auth_token
    鈫?鐩存帴浣跨敤 鈫?楠岃瘉
```

---

## 涓夈€乀oken 楠岃瘉

```yaml
楠岃瘉鏂瑰紡:
  浼樺厛浣跨敤 Swagger 涓凡鐭ョ殑杞婚噺 API锛堝 GetPlatformDropList锛?
    POST {api_base}/api/ThirdInvoice/GetPlatformDropList
    -H "Authorization: Bearer {token}" -d '{"settleCycle":1}'
  
  鎴愬姛: 200 鈫?Token 鏈夋晥 鉁?  澶辫触: 401/403 鈫?Token 鏃犳晥/杩囨湡 鈫?閲嶆柊璧版楠?浼樺厛绾ч摼
  澶辫触: 缃戠粶閿欒 鈫?鏍囪鐜涓嶅彲鐢?
  涓嶈鐢?curl 鐚滄祴楠岃瘉绔偣銆備紭鍏堢敤 Swagger JSON 涓凡鏈夌殑 GET/POST 绔偣銆?```

---

## 涓?涓€銆乤gent-browser 鎵ц瑙勮寖锛圵indows/PowerShell 宸紓锛?
```yaml
# 鈿狅笍 涓ユ牸绂佹鐩存帴浣跨敤鐨勫懡浠わ細
#   - agent-browser click @ref     → PowerShell 把 @ref 当空变量
  - agent-browser fill @ref      → 同上
  - agent-browser type @ref      → 同上

  @ref 的正确写法（全部加双引号）:
    点击: agent-browser click "@e61"
    输入: agent-browser type "@e168" "文本"
    填充: agent-browser fill "@e169" "文本"
    获取: agent-browser get text "@e1"

  Ant Design 受控组件特殊处理（fill/type 不触发 React onChange）:
    输入框聚焦: agent-browser eval "document.querySelector('#username')?.focus()"
    真实击键（触 React onChange）: agent-browser keyboard type "109013"
    Tab 移出触发 blur: agent-browser press "Tab"
  
  窗口管理r keyboard type "鏂囨湰"
  
  閿洏:
    agent-browser press "Tab" / agent-browser press "Enter"

  鏌ョ湅:
    1. agent-browser eval "document.querySelector('input#id')?.value"
    2. agent-browser get url --json

绐楀彛绠＄悊:
  - 鍏?close --all 娓呯悊娈嬬暀 鈫?鍐?open 鏂颁細璇?  - 棣栨 open 蹇呴』甯?--headed --args "--start-maximized,--disable-password-manager,--disable-password-manager-reauthentication,--disable-save-password-bubble,--disable-password-leak-detection"
  - 鐧诲綍鍚庡厛 snapshot 纭椤甸潰绋冲畾 鈫?鍐嶅鑸埌鐩爣椤?
鐧诲綍绫诲瀷C1锛堝伐鍙风櫥褰曪紝Keycloak 缁熶竴璁よ瘉锛?
  - 鐢?eval 鐐瑰嚮 label 鍒囨崲鍒板伐鍙风櫥褰曪紙涓嶇敤 @ref锛?    agent-browser eval "document.querySelector('label')?.click()"
  - 鐢?eval 鐩存帴濉€?    agent-browser eval "document.querySelector('#username').value='109013'; document.querySelector('#password').value='Arvin@1314!'"
  - 鐢?eval 鐐圭櫥褰?    agent-browser eval "document.querySelector('#kc-login').click()"
```

## 鍥涖€侀敊璇鐞?
```yaml
鐧诲綍澶辫触澶勭悊:
  - 椤甸潰涓婃樉绀?鐢ㄦ埛鍚嶆垨瀵嗙爜閿欒" 鈫?纭鍑瘉鏃犺锛屾渶澶氶噸璇?1 娆?  - 椤甸潰璺宠浆鍒伴敊璇〉(404/500) 鈫?鏍囪鐜涓嶅彲鐢?  - 鐧诲綍鍚?snapshot 绌虹櫧 鈫?绛夊緟(3s) 鈫?鍐?snapshot 鈫?浠嶇┖鐧?鈫?鍒锋柊椤甸潰閲嶈瘯
  - 鐧诲綍椤甸潰鍖呭惈楠岃瘉鐮?鈫?鏍囪"闇€瑕佷汉宸ヤ粙鍏ワ細鐧诲綍椤垫湁楠岃瘉鐮?
  
Token 鎻愬彇澶辫触澶勭悊:
  - localStorage/Cookies 鍧囦负绌?鈫?妫€鏌ラ〉闈笂鏄惁鏈?鐧诲綍"鎸夐挳锛堟湭鐪熸鐧诲綍锛?  - 鎵€鏈変紭鍏堢骇鍧囧け璐?鈫?鏈€鍚庢墜娈碉細鎻愮ず鐢ㄦ埛鎵嬪姩鎻愪緵 Token
```

---

## 浜斻€佺姝簨椤?
```yaml
鉀?绂佹:
  1. 绂佹璺宠繃 agent-browser 鐩存帴鐢?curl 鐚滄祴 API 鐧诲綍绔偣
  2. 绂佹鍦ㄦ病鏈?Swagger 鏂囨。鐨勬儏鍐典笅鐩茬洰灏濊瘯 /api/Account/Login 绛夊父瑙佽矾寰?  3. 绂佹鍦?Token 鎻愬彇澶辫触鍚庣户缁皾璇曡秴杩?3 涓笉鍚?API 绔偣
  4. 绂佹鎵撳紑椤甸潰鏃朵笉鍔?--args "--start-maximized,--disable-password-manager,--disable-password-manager-reauthentication,--disable-save-password-bubble,--disable-password-leak-detection" 鍙傛暟
  5. 绂佹鐧诲綍鎴愬姛鍚庝笉楠岃瘉 Token 灏辩洿鎺ヤ娇鐢?  6. 绂佹鍦ㄧ幆澧冨垏鎹?鐧诲綍鍚庣珛鍗崇敤 open URL 璺宠浆鍒版繁灞傞〉闈€?     鍘熷洜: 鐧诲綍鎴栫幆澧冨垏鎹㈠悗锛屽簲鐢ㄥ彲鑳介渶瑕佹椂闂村畬鎴愬垵濮嬪寲锛堢敤鎴蜂俊鎭姞杞姐€佹潈闄愭牎楠岀瓑锛夈€?     姝ゆ椂 open 涓€涓繁灞?URL锛屽簲鐢ㄥ彲鑳藉洜鍒濆鍖栨湭瀹屾垚鑰岄噸瀹氬悜鍥炵櫥褰曢〉銆?     姝ｇ‘鍋氭硶: 鐜鍒囨崲鍚庡厛 snapshot 纭椤甸潰绋冲畾锛堝鐪嬪埌瀵艰埅鑿滃崟/棣栭〉鍐呭锛夛紝
     鍐嶉€氳繃鑿滃崟鐐瑰嚮鎴?open URL 瀵艰埅銆備袱绉嶅鑸柟寮忓潎鍙紝鍏抽敭鏄‘璁ょ姸鎬佺ǔ瀹氬悗鍐嶆搷浣溿€?  7. 绂佹鍦?daemon 宸茶繍琛屽悗鍐嶆浼?--headed / --args 鍙傛暟锛堣繖浜涘弬鏁颁細琚拷鐣ワ紝
     鎻愮ず "daemon already running"锛?
鉁?蹇呴』:
  1. 蹇呴』鍏堢敤 agent-browser 鎵撳紑椤甸潰瀹屾垚鐧诲綍
  2. 蹇呴』鏈€澶у寲绐楀彛: 棣栨 open 浣跨敤 --args "--start-maximized,--disable-password-manager,--disable-password-manager-reauthentication,--disable-save-password-bubble,--disable-password-leak-detection"
  3. 蹇呴』楠岃瘉绐楀彛灏哄: 棣栨 open 鍚庣珛鍗?eval window.innerWidth/innerHeight锛?     濡傚搴?1920 鍒欑敤 agent-browser set viewport 1920 1080 鍏滃簳
  4. 蹇呴』鎸変紭鍏堢骇閾炬彁鍙?Token锛坙ocalStorage 鈫?Cookies 鈫?JS 鍙橀噺 鈫?API 鈫?閰嶇疆鏂囦欢锛?  5. 蹇呴』鐢ㄥ凡鐭?API 绔偣楠岃瘉 Token 鏈夋晥鎬?  6. 蹇呴』鎴浘淇濆瓨鐧诲綍缁撴灉
  7. 鐧诲綍/鐜鍒囨崲鍚庯紝蹇呴』鍏?snapshot 纭椤甸潰绋冲畾锛堝鑸彍鍗曘€佺敤鎴蜂俊鎭瓑宸叉覆鏌擄級锛?     鍐嶅鑸埌鐩爣椤甸潰銆傚鑸柟寮忓彲浠ユ槸鑿滃崟鐐瑰嚮鎴?open URL锛屼袱绉嶅潎鍙?```
