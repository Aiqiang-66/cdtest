# XEY5 SRT 人名字幕比对测试报告（v4 - 带上下文）

**执行时间**: 2026-07-31 14:23:38

## 1. 测试结论

**结论：不通过 ❌（10/10 集存在问题）**

核心问题：18条错标（角色→Narration）, 225条无依据新增Narration

## 2. 汇总统计

| 指标 | 数值 |
| --- | ---: |
| 比对集数 | 10 |
| 通过集数 | 0 |
| 不通过集数 | 10 |
| 比对字幕总条数 | 322 |
| 原始带人名标注 | 97 |
| 正确保留人名 | 79 (81.4%) |
| 错标 | 18 |
| 漏标 | 0 |
| 无依据新增标注 | 225 |
| 台词正文不一致 | 0 |
| 时间轴不一致 | 0 |

## 3. 逐集比对结果

| 集数 | 字幕数 | 原始标注 | 正确保留 | 错标 | 漏标 | 新增 | 结论 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 39 | 4 | 4 | 0 | 0 | 35 | ❌ |
| 2 | 38 | 10 | 10 | 0 | 0 | 28 | ❌ |
| 3 | 31 | 9 | 9 | 0 | 0 | 22 | ❌ |
| 4 | 32 | 12 | 12 | 0 | 0 | 20 | ❌ |
| 5 | 29 | 8 | 8 | 0 | 0 | 21 | ❌ |
| 6 | 30 | 11 | 11 | 0 | 0 | 19 | ❌ |
| 7 | 27 | 14 | 4 | 10 | 0 | 13 | ❌ |
| 8 | 43 | 11 | 11 | 0 | 0 | 32 | ❌ |
| 9 | 34 | 13 | 5 | 8 | 0 | 21 | ❌ |
| 10 | 19 | 5 | 5 | 0 | 0 | 14 | ❌ |

## 4. 错标详情（共 18 条）

> 原始剧本明确标注了角色名，模型输出将其替换为 `Narration`。

### 第7集 第2条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:03,000 --> 00:00:05,300` |
| 原始标注 | `Alex` |
| 模型标注 | `Narration` |
| 原始台词 | `Alex: Are you fucking insane? Noah!` |
| 模型台词 | `Narration: Are you fucking insane? Noah!` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:02,233] Narration: I glance up and spot Noah in front of us.
  >>> #2 [00:00:03,000 --> 00:00:05,300] Alex: Are you fucking insane? Noah!
      #3 [00:00:07,033 --> 00:00:08,266] Noah: Why are you with Sadie?
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:02,233] Narration: I glance up and spot Noah in front of us.
  >>> #2 [00:00:03,000 --> 00:00:05,300] Narration: Are you fucking insane? Noah!
      #3 [00:00:07,033 --> 00:00:08,266] Narration: Why are you with Sadie?
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
```

</details>

### 第7集 第3条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:07,033 --> 00:00:08,266` |
| 原始标注 | `Noah` |
| 模型标注 | `Narration` |
| 原始台词 | `Noah: Why are you with Sadie?` |
| 模型台词 | `Narration: Why are you with Sadie?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:02,233] Narration: I glance up and spot Noah in front of us.
      #2 [00:00:03,000 --> 00:00:05,300] Alex: Are you fucking insane? Noah!
  >>> #3 [00:00:07,033 --> 00:00:08,266] Noah: Why are you with Sadie?
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
      #5 [00:00:12,400 --> 00:00:14,100] Sadie: There's no need to explain, Alex.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:02,233] Narration: I glance up and spot Noah in front of us.
      #2 [00:00:03,000 --> 00:00:05,300] Narration: Are you fucking insane? Noah!
  >>> #3 [00:00:07,033 --> 00:00:08,266] Narration: Why are you with Sadie?
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
      #5 [00:00:12,400 --> 00:00:14,100] Narration: There's no need to explain, Alex.
```

</details>

### 第7集 第5条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:12,400 --> 00:00:14,100` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: There's no need to explain, Alex.` |
| 模型台词 | `Narration: There's no need to explain, Alex.` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #3 [00:00:07,033 --> 00:00:08,266] Noah: Why are you with Sadie?
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
  >>> #5 [00:00:12,400 --> 00:00:14,100] Sadie: There's no need to explain, Alex.
      #6 [00:00:14,400 --> 00:00:16,266] I have nothing to do with him anymore.
      #7 [00:00:19,600 --> 00:00:20,433] Does it hurt?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #3 [00:00:07,033 --> 00:00:08,266] Narration: Why are you with Sadie?
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
  >>> #5 [00:00:12,400 --> 00:00:14,100] Narration: There's no need to explain, Alex.
      #6 [00:00:14,400 --> 00:00:16,266] Narration: I have nothing to do with him anymore.
      #7 [00:00:19,600 --> 00:00:20,433] Narration: Does it hurt?
```

</details>

### 第7集 第11条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:28,333 --> 00:00:29,351` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: What are you doing?` |
| 模型台词 | `Narration: What are you doing?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
      #10 [00:00:24,200 --> 00:00:27,100] He grabs my wrist and drags me toward the elevator.
  >>> #11 [00:00:28,333 --> 00:00:29,351] Sadie: What are you doing?
      #12 [00:00:29,491 --> 00:00:30,217] Let me go!
      #13 [00:00:30,366 --> 00:00:32,289] Narration: He drags me to my apartment door,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
      #10 [00:00:24,200 --> 00:00:27,100] Narration: He grabs my wrist and drags me toward the elevator.
  >>> #11 [00:00:28,333 --> 00:00:29,351] Narration: What are you doing?
      #12 [00:00:29,491 --> 00:00:30,217] Narration: Let me go!
      #13 [00:00:30,366 --> 00:00:32,289] Narration: He drags me to my apartment door,
```

</details>

### 第7集 第15条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:34,966 --> 00:00:36,618` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: What the hell is wrong with you!` |
| 模型台词 | `Narration: What the hell is wrong with you!` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #13 [00:00:30,366 --> 00:00:32,289] Narration: He drags me to my apartment door,
      #14 [00:00:32,289 --> 00:00:33,083] and kicks it open.
  >>> #15 [00:00:34,966 --> 00:00:36,618] Sadie: What the hell is wrong with you!
      #16 [00:00:36,866 --> 00:00:37,666] Noah: What's wrong with me?
      #17 [00:00:37,866 --> 00:00:39,133] I want to know why you're with him!
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #13 [00:00:30,366 --> 00:00:32,289] Narration: He drags me to my apartment door,
      #14 [00:00:32,289 --> 00:00:33,083] Narration: and kicks it open.
  >>> #15 [00:00:34,966 --> 00:00:36,618] Narration: What the hell is wrong with you!
      #16 [00:00:36,866 --> 00:00:37,666] Narration: What's wrong with me?
      #17 [00:00:37,866 --> 00:00:39,133] Narration: I want to know why you're with him!
```

</details>

### 第7集 第16条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:36,866 --> 00:00:37,666` |
| 原始标注 | `Noah` |
| 模型标注 | `Narration` |
| 原始台词 | `Noah: What's wrong with me?` |
| 模型台词 | `Narration: What's wrong with me?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #14 [00:00:32,289 --> 00:00:33,083] and kicks it open.
      #15 [00:00:34,966 --> 00:00:36,618] Sadie: What the hell is wrong with you!
  >>> #16 [00:00:36,866 --> 00:00:37,666] Noah: What's wrong with me?
      #17 [00:00:37,866 --> 00:00:39,133] I want to know why you're with him!
      #18 [00:00:41,466 --> 00:00:42,466] Sadie: Are you following me?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #14 [00:00:32,289 --> 00:00:33,083] Narration: and kicks it open.
      #15 [00:00:34,966 --> 00:00:36,618] Narration: What the hell is wrong with you!
  >>> #16 [00:00:36,866 --> 00:00:37,666] Narration: What's wrong with me?
      #17 [00:00:37,866 --> 00:00:39,133] Narration: I want to know why you're with him!
      #18 [00:00:41,466 --> 00:00:42,466] Narration: Are you following me?
```

</details>

### 第7集 第18条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:41,466 --> 00:00:42,466` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: Are you following me?` |
| 模型台词 | `Narration: Are you following me?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #16 [00:00:36,866 --> 00:00:37,666] Noah: What's wrong with me?
      #17 [00:00:37,866 --> 00:00:39,133] I want to know why you're with him!
  >>> #18 [00:00:41,466 --> 00:00:42,466] Sadie: Are you following me?
      #19 [00:00:44,766 --> 00:00:45,866] Noah: Feeling guilty, huh?
      #20 [00:00:46,400 --> 00:00:47,600] Sadie: Why should I feel guilty?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #16 [00:00:36,866 --> 00:00:37,666] Narration: What's wrong with me?
      #17 [00:00:37,866 --> 00:00:39,133] Narration: I want to know why you're with him!
  >>> #18 [00:00:41,466 --> 00:00:42,466] Narration: Are you following me?
      #19 [00:00:44,766 --> 00:00:45,866] Narration: Feeling guilty, huh?
      #20 [00:00:46,400 --> 00:00:47,600] Narration: Why should I feel guilty?
```

</details>

### 第7集 第19条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:44,766 --> 00:00:45,866` |
| 原始标注 | `Noah` |
| 模型标注 | `Narration` |
| 原始台词 | `Noah: Feeling guilty, huh?` |
| 模型台词 | `Narration: Feeling guilty, huh?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #17 [00:00:37,866 --> 00:00:39,133] I want to know why you're with him!
      #18 [00:00:41,466 --> 00:00:42,466] Sadie: Are you following me?
  >>> #19 [00:00:44,766 --> 00:00:45,866] Noah: Feeling guilty, huh?
      #20 [00:00:46,400 --> 00:00:47,600] Sadie: Why should I feel guilty?
      #21 [00:00:48,300 --> 00:00:49,666] We're about to get divorced.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #17 [00:00:37,866 --> 00:00:39,133] Narration: I want to know why you're with him!
      #18 [00:00:41,466 --> 00:00:42,466] Narration: Are you following me?
  >>> #19 [00:00:44,766 --> 00:00:45,866] Narration: Feeling guilty, huh?
      #20 [00:00:46,400 --> 00:00:47,600] Narration: Why should I feel guilty?
      #21 [00:00:48,300 --> 00:00:49,666] Narration: We're about to get divorced.
```

</details>

### 第7集 第20条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:46,400 --> 00:00:47,600` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: Why should I feel guilty?` |
| 模型台词 | `Narration: Why should I feel guilty?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #18 [00:00:41,466 --> 00:00:42,466] Sadie: Are you following me?
      #19 [00:00:44,766 --> 00:00:45,866] Noah: Feeling guilty, huh?
  >>> #20 [00:00:46,400 --> 00:00:47,600] Sadie: Why should I feel guilty?
      #21 [00:00:48,300 --> 00:00:49,666] We're about to get divorced.
      #22 [00:00:49,966 --> 00:00:52,300] Who I spend time with is none of your business.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #18 [00:00:41,466 --> 00:00:42,466] Narration: Are you following me?
      #19 [00:00:44,766 --> 00:00:45,866] Narration: Feeling guilty, huh?
  >>> #20 [00:00:46,400 --> 00:00:47,600] Narration: Why should I feel guilty?
      #21 [00:00:48,300 --> 00:00:49,666] Narration: We're about to get divorced.
      #22 [00:00:49,966 --> 00:00:52,300] Narration: Who I spend time with is none of your business.
```

</details>

### 第7集 第23条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:53,966 --> 00:00:54,700` |
| 原始标注 | `Noah` |
| 模型标注 | `Narration` |
| 原始台词 | `Noah: Divorce?` |
| 模型台词 | `Narration: Divorce?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #21 [00:00:48,300 --> 00:00:49,666] We're about to get divorced.
      #22 [00:00:49,966 --> 00:00:52,300] Who I spend time with is none of your business.
  >>> #23 [00:00:53,966 --> 00:00:54,700] Noah: Divorce?
      #24 [00:00:55,633 --> 00:00:56,200] Sadie,
      #25 [00:00:56,200 --> 00:00:57,066] I told you.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #21 [00:00:48,300 --> 00:00:49,666] Narration: We're about to get divorced.
      #22 [00:00:49,966 --> 00:00:52,300] Narration: Who I spend time with is none of your business.
  >>> #23 [00:00:53,966 --> 00:00:54,700] Narration: Divorce?
      #24 [00:00:55,633 --> 00:00:56,200] Narration: Sadie,
      #25 [00:00:56,200 --> 00:00:57,066] Narration: I told you.
```

</details>

### 第9集 第2条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:03,800 --> 00:00:04,833` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: Was it you?` |
| 模型台词 | `Narration: Was it you?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,033 --> 00:00:03,400] Narration: Kyla approaches, her face full of smug satisfaction.
  >>> #2 [00:00:03,800 --> 00:00:04,833] Sadie: Was it you?
      #3 [00:00:04,900 --> 00:00:06,866] Kyla: I heard you've loved Noah for ten years,
      #4 [00:00:06,866 --> 00:00:07,900] but funny thing,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,033 --> 00:00:03,400] Narration: Kyla approaches, her face full of smug satisfaction.
  >>> #2 [00:00:03,800 --> 00:00:04,833] Narration: Was it you?
      #3 [00:00:04,900 --> 00:00:06,866] Narration: I heard you've loved Noah for ten years,
      #4 [00:00:06,866 --> 00:00:07,900] Narration: but funny thing,
```

</details>

### 第9集 第3条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:04,900 --> 00:00:06,866` |
| 原始标注 | `Kyla` |
| 模型标注 | `Narration` |
| 原始台词 | `Kyla: I heard you've loved Noah for ten years,` |
| 模型台词 | `Narration: I heard you've loved Noah for ten years,` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,033 --> 00:00:03,400] Narration: Kyla approaches, her face full of smug satisfaction.
      #2 [00:00:03,800 --> 00:00:04,833] Sadie: Was it you?
  >>> #3 [00:00:04,900 --> 00:00:06,866] Kyla: I heard you've loved Noah for ten years,
      #4 [00:00:06,866 --> 00:00:07,900] but funny thing,
      #5 [00:00:08,266 --> 00:00:10,200] he's loved me for just as long.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,033 --> 00:00:03,400] Narration: Kyla approaches, her face full of smug satisfaction.
      #2 [00:00:03,800 --> 00:00:04,833] Narration: Was it you?
  >>> #3 [00:00:04,900 --> 00:00:06,866] Narration: I heard you've loved Noah for ten years,
      #4 [00:00:06,866 --> 00:00:07,900] Narration: but funny thing,
      #5 [00:00:08,266 --> 00:00:10,200] Narration: he's loved me for just as long.
```

</details>

### 第9集 第9条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:14,800 --> 00:00:16,866` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: Are you so certain he'll choose you?` |
| 模型台词 | `Narration: Are you so certain he'll choose you?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #7 [00:00:11,100 --> 00:00:12,733] do you think he'll make your marriage public,
      #8 [00:00:12,733 --> 00:00:14,066] or will he just discard you?
  >>> #9 [00:00:14,800 --> 00:00:16,866] Sadie: Are you so certain he'll choose you?
      #10 [00:00:19,266 --> 00:00:21,333] I've shared his bed for two years.
      #11 [00:00:22,100 --> 00:00:24,700] Do you honestly believe his desires mean nothing?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #7 [00:00:11,100 --> 00:00:12,733] Narration: do you think he'll make your marriage public,
      #8 [00:00:12,733 --> 00:00:14,066] Narration: or will he just discard you?
  >>> #9 [00:00:14,800 --> 00:00:16,866] Narration: Are you so certain he'll choose you?
      #10 [00:00:19,266 --> 00:00:21,333] Narration: I've shared his bed for two years.
      #11 [00:00:22,100 --> 00:00:24,700] Narration: Do you honestly believe his desires mean nothing?
```

</details>

### 第9集 第15条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:31,900 --> 00:00:33,533` |
| 原始标注 | `Kyla` |
| 模型标注 | `Narration` |
| 原始台词 | `Kyla: Please don't blame Noah.` |
| 模型台词 | `Narration: Please don't blame Noah.` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #13 [00:00:28,033 --> 00:00:29,100] but suddenly stops
      #14 [00:00:29,100 --> 00:00:31,266] and puts on a pitiful expression instead.
  >>> #15 [00:00:31,900 --> 00:00:33,533] Kyla: Please don't blame Noah.
      #16 [00:00:33,933 --> 00:00:35,400] It's my fault.
      #17 [00:00:35,633 --> 00:00:37,533] Noah: What bullshit did you say, Sadie?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #13 [00:00:28,033 --> 00:00:29,100] Narration: but suddenly stops
      #14 [00:00:29,100 --> 00:00:31,266] Narration: and puts on a pitiful expression instead.
  >>> #15 [00:00:31,900 --> 00:00:33,533] Narration: Please don't blame Noah.
      #16 [00:00:33,933 --> 00:00:35,400] Narration: It's my fault.
      #17 [00:00:35,633 --> 00:00:37,533] Narration: What bullshit did you say, Sadie?
```

</details>

### 第9集 第17条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:35,633 --> 00:00:37,533` |
| 原始标注 | `Noah` |
| 模型标注 | `Narration` |
| 原始台词 | `Noah: What bullshit did you say, Sadie?` |
| 模型台词 | `Narration: What bullshit did you say, Sadie?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #15 [00:00:31,900 --> 00:00:33,533] Kyla: Please don't blame Noah.
      #16 [00:00:33,933 --> 00:00:35,400] It's my fault.
  >>> #17 [00:00:35,633 --> 00:00:37,533] Noah: What bullshit did you say, Sadie?
      #18 [00:00:37,733 --> 00:00:39,200] Narration: Noah suddenly appears,
      #19 [00:00:39,200 --> 00:00:41,433] and his reproachful gaze fixates on me.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #15 [00:00:31,900 --> 00:00:33,533] Narration: Please don't blame Noah.
      #16 [00:00:33,933 --> 00:00:35,400] Narration: It's my fault.
  >>> #17 [00:00:35,633 --> 00:00:37,533] Narration: What bullshit did you say, Sadie?
      #18 [00:00:37,733 --> 00:00:39,200] Narration: Noah suddenly appears,
      #19 [00:00:39,200 --> 00:00:41,433] Narration: and his reproachful gaze fixates on me.
```

</details>

### 第9集 第24条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:57,433 --> 00:00:59,100` |
| 原始标注 | `Noah` |
| 模型标注 | `Narration` |
| 原始台词 | `Noah: Sadie! We're going to the hospital!` |
| 模型台词 | `Narration: Sadie! We're going to the hospital!` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #22 [00:00:51,900 --> 00:00:53,400] I rush to the restroom.
      #23 [00:00:53,566 --> 00:00:55,500] I lean over the sink as I retch.
  >>> #24 [00:00:57,433 --> 00:00:59,100] Noah: Sadie! We're going to the hospital!
      #25 [00:00:59,733 --> 00:01:02,133] Sadie: No need. Just something I ate.
      #26 [00:01:02,366 --> 00:01:04,833] Mr. Wall, please have some decency,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #22 [00:00:51,900 --> 00:00:53,400] Narration: I rush to the restroom.
      #23 [00:00:53,566 --> 00:00:55,500] Narration: I lean over the sink as I retch.
  >>> #24 [00:00:57,433 --> 00:00:59,100] Narration: Sadie! We're going to the hospital!
      #25 [00:00:59,733 --> 00:01:02,133] Narration: No need. Just something I ate.
      #26 [00:01:02,366 --> 00:01:04,833] Narration: Mr. Wall, please have some decency,
```

</details>

### 第9集 第25条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:00:59,733 --> 00:01:02,133` |
| 原始标注 | `Sadie` |
| 模型标注 | `Narration` |
| 原始台词 | `Sadie: No need. Just something I ate.` |
| 模型台词 | `Narration: No need. Just something I ate.` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #23 [00:00:53,566 --> 00:00:55,500] I lean over the sink as I retch.
      #24 [00:00:57,433 --> 00:00:59,100] Noah: Sadie! We're going to the hospital!
  >>> #25 [00:00:59,733 --> 00:01:02,133] Sadie: No need. Just something I ate.
      #26 [00:01:02,366 --> 00:01:04,833] Mr. Wall, please have some decency,
      #27 [00:01:05,300 --> 00:01:06,600] we're about to get divorced!
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #23 [00:00:53,566 --> 00:00:55,500] Narration: I lean over the sink as I retch.
      #24 [00:00:57,433 --> 00:00:59,100] Narration: Sadie! We're going to the hospital!
  >>> #25 [00:00:59,733 --> 00:01:02,133] Narration: No need. Just something I ate.
      #26 [00:01:02,366 --> 00:01:04,833] Narration: Mr. Wall, please have some decency,
      #27 [00:01:05,300 --> 00:01:06,600] Narration: we're about to get divorced!
```

</details>

### 第9集 第29条

| 项目 | 内容 |
| --- | --- |
| 时间轴 | `00:01:11,933 --> 00:01:13,233` |
| 原始标注 | `Kyla` |
| 模型标注 | `Narration` |
| 原始台词 | `Kyla: Noah, where are you?` |
| 模型台词 | `Narration: Noah, where are you?` |

<details>
<summary>📋 原始剧本上下文</summary>

```
      #27 [00:01:05,300 --> 00:01:06,600] we're about to get divorced!
      #28 [00:01:06,766 --> 00:01:09,033] Narration: His phone rings. It's Kyla.
  >>> #29 [00:01:11,933 --> 00:01:13,233] Kyla: Noah, where are you?
      #30 [00:01:13,233 --> 00:01:14,833] There's a contract that needs your attention.
      #31 [00:01:14,900 --> 00:01:16,333] Narration: I slide to the floor,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #27 [00:01:05,300 --> 00:01:06,600] Narration: we're about to get divorced!
      #28 [00:01:06,766 --> 00:01:09,033] Narration: His phone rings. It's Kyla.
  >>> #29 [00:01:11,933 --> 00:01:13,233] Narration: Noah, where are you?
      #30 [00:01:13,233 --> 00:01:14,833] Narration: There's a contract that needs your attention.
      #31 [00:01:14,900 --> 00:01:16,333] Narration: I slide to the floor,
```

</details>


## 5. 无依据新增 Narration 详情（共 225 条，每集展示前5条）

> 原始剧本无前缀的纯台词，模型擅自加上 `Narration:` 前缀。

### 第1集（35条，展示前5条）

**第2条** `00:00:03,200 --> 00:00:05,900`

- 原始台词: `I wake up from my sleep and meet a pair of deep eyes.`
- 模型输出: `Narration: Narration: I wake up from my sleep and meet a pair of deep eyes.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:01,266 --> 00:00:02,933] Narration: Late at night, in the bedroom.
  >>> #2 [00:00:03,200 --> 00:00:05,900] I wake up from my sleep and meet a pair of deep eyes.
      #3 [00:00:06,200 --> 00:00:08,033] My husband Noah Wall has returned,
      #4 [00:00:08,200 --> 00:00:09,266] smelling of alcohol,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:01,266 --> 00:00:02,933] Narration: Late at night, in the bedroom.
  >>> #2 [00:00:03,200 --> 00:00:05,900] Narration: I wake up from my sleep and meet a pair of deep eyes.
      #3 [00:00:06,200 --> 00:00:08,033] Narration: My husband Noah Wall has returned,
      #4 [00:00:08,200 --> 00:00:09,266] Narration: smelling of alcohol,
```

</details>

**第3条** `00:00:06,200 --> 00:00:08,033`

- 原始台词: `My husband Noah Wall has returned,`
- 模型输出: `Narration: Narration: My husband Noah Wall has returned,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:01,266 --> 00:00:02,933] Narration: Late at night, in the bedroom.
      #2 [00:00:03,200 --> 00:00:05,900] I wake up from my sleep and meet a pair of deep eyes.
  >>> #3 [00:00:06,200 --> 00:00:08,033] My husband Noah Wall has returned,
      #4 [00:00:08,200 --> 00:00:09,266] smelling of alcohol,
      #5 [00:00:09,400 --> 00:00:11,000] his kiss domineering.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:01,266 --> 00:00:02,933] Narration: Late at night, in the bedroom.
      #2 [00:00:03,200 --> 00:00:05,900] Narration: I wake up from my sleep and meet a pair of deep eyes.
  >>> #3 [00:00:06,200 --> 00:00:08,033] Narration: My husband Noah Wall has returned,
      #4 [00:00:08,200 --> 00:00:09,266] Narration: smelling of alcohol,
      #5 [00:00:09,400 --> 00:00:11,000] Narration: his kiss domineering.
```

</details>

**第4条** `00:00:08,200 --> 00:00:09,266`

- 原始台词: `smelling of alcohol,`
- 模型输出: `Narration: Narration: smelling of alcohol,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:03,200 --> 00:00:05,900] I wake up from my sleep and meet a pair of deep eyes.
      #3 [00:00:06,200 --> 00:00:08,033] My husband Noah Wall has returned,
  >>> #4 [00:00:08,200 --> 00:00:09,266] smelling of alcohol,
      #5 [00:00:09,400 --> 00:00:11,000] his kiss domineering.
      #6 [00:00:11,266 --> 00:00:12,900] Today is our second anniversary.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:03,200 --> 00:00:05,900] Narration: I wake up from my sleep and meet a pair of deep eyes.
      #3 [00:00:06,200 --> 00:00:08,033] Narration: My husband Noah Wall has returned,
  >>> #4 [00:00:08,200 --> 00:00:09,266] Narration: smelling of alcohol,
      #5 [00:00:09,400 --> 00:00:11,000] Narration: his kiss domineering.
      #6 [00:00:11,266 --> 00:00:12,900] Narration: Today is our second anniversary.
```

</details>

**第5条** `00:00:09,400 --> 00:00:11,000`

- 原始台词: `his kiss domineering.`
- 模型输出: `Narration: Narration: his kiss domineering.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #3 [00:00:06,200 --> 00:00:08,033] My husband Noah Wall has returned,
      #4 [00:00:08,200 --> 00:00:09,266] smelling of alcohol,
  >>> #5 [00:00:09,400 --> 00:00:11,000] his kiss domineering.
      #6 [00:00:11,266 --> 00:00:12,900] Today is our second anniversary.
      #7 [00:00:12,900 --> 00:00:14,300] I don't want to ruin the mood,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #3 [00:00:06,200 --> 00:00:08,033] Narration: My husband Noah Wall has returned,
      #4 [00:00:08,200 --> 00:00:09,266] Narration: smelling of alcohol,
  >>> #5 [00:00:09,400 --> 00:00:11,000] Narration: his kiss domineering.
      #6 [00:00:11,266 --> 00:00:12,900] Narration: Today is our second anniversary.
      #7 [00:00:12,900 --> 00:00:14,300] Narration: I don't want to ruin the mood,
```

</details>

**第6条** `00:00:11,266 --> 00:00:12,900`

- 原始台词: `Today is our second anniversary.`
- 模型输出: `Narration: Narration: Today is our second anniversary.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #4 [00:00:08,200 --> 00:00:09,266] smelling of alcohol,
      #5 [00:00:09,400 --> 00:00:11,000] his kiss domineering.
  >>> #6 [00:00:11,266 --> 00:00:12,900] Today is our second anniversary.
      #7 [00:00:12,900 --> 00:00:14,300] I don't want to ruin the mood,
      #8 [00:00:14,300 --> 00:00:16,133] so I close my eyes and comply.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #4 [00:00:08,200 --> 00:00:09,266] Narration: smelling of alcohol,
      #5 [00:00:09,400 --> 00:00:11,000] Narration: his kiss domineering.
  >>> #6 [00:00:11,266 --> 00:00:12,900] Narration: Today is our second anniversary.
      #7 [00:00:12,900 --> 00:00:14,300] Narration: I don't want to ruin the mood,
      #8 [00:00:14,300 --> 00:00:16,133] Narration: so I close my eyes and comply.
```

</details>

### 第2集（28条，展示前5条）

**第2条** `00:00:00,900 --> 00:00:02,600`

- 原始台词: `I hear sounds from the study.`
- 模型输出: `Narration: Narration: I hear sounds from the study.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,900] Narration: Late at night,
  >>> #2 [00:00:00,900 --> 00:00:02,600] I hear sounds from the study.
      #3 [00:00:03,066 --> 00:00:04,300] As I approach the door,
      #4 [00:00:04,600 --> 00:00:06,100] I hear Alex's voice.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,900] Narration: Late at night,
  >>> #2 [00:00:00,900 --> 00:00:02,600] Narration: I hear sounds from the study.
      #3 [00:00:03,066 --> 00:00:04,300] Narration: As I approach the door,
      #4 [00:00:04,600 --> 00:00:06,100] Narration: I hear Alex's voice.
```

</details>

**第3条** `00:00:03,066 --> 00:00:04,300`

- 原始台词: `As I approach the door,`
- 模型输出: `Narration: Narration: As I approach the door,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,900] Narration: Late at night,
      #2 [00:00:00,900 --> 00:00:02,600] I hear sounds from the study.
  >>> #3 [00:00:03,066 --> 00:00:04,300] As I approach the door,
      #4 [00:00:04,600 --> 00:00:06,100] I hear Alex's voice.
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,900] Narration: Late at night,
      #2 [00:00:00,900 --> 00:00:02,600] Narration: I hear sounds from the study.
  >>> #3 [00:00:03,066 --> 00:00:04,300] Narration: As I approach the door,
      #4 [00:00:04,600 --> 00:00:06,100] Narration: I hear Alex's voice.
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
```

</details>

**第4条** `00:00:04,600 --> 00:00:06,100`

- 原始台词: `I hear Alex's voice.`
- 模型输出: `Narration: Narration: I hear Alex's voice.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:00,900 --> 00:00:02,600] I hear sounds from the study.
      #3 [00:00:03,066 --> 00:00:04,300] As I approach the door,
  >>> #4 [00:00:04,600 --> 00:00:06,100] I hear Alex's voice.
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
      #6 [00:00:15,266 --> 00:00:16,233] What about Sadie?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:00,900 --> 00:00:02,600] Narration: I hear sounds from the study.
      #3 [00:00:03,066 --> 00:00:04,300] Narration: As I approach the door,
  >>> #4 [00:00:04,600 --> 00:00:06,100] Narration: I hear Alex's voice.
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
      #6 [00:00:15,266 --> 00:00:16,233] Alex: What about Sadie?
```

</details>

**第6条** `00:00:15,266 --> 00:00:16,233`

- 原始台词: `What about Sadie?`
- 模型输出: `Alex: Alex: What about Sadie?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #4 [00:00:04,600 --> 00:00:06,100] I hear Alex's voice.
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
  >>> #6 [00:00:15,266 --> 00:00:16,233] What about Sadie?
      #7 [00:00:17,300 --> 00:00:18,666] After two years of marriage,
      #8 [00:00:18,666 --> 00:00:21,400] you can't possibly have no feelings for her at all,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #4 [00:00:04,600 --> 00:00:06,100] Narration: I hear Alex's voice.
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
  >>> #6 [00:00:15,266 --> 00:00:16,233] Alex: What about Sadie?
      #7 [00:00:17,300 --> 00:00:18,666] Alex: After two years of marriage,
      #8 [00:00:18,666 --> 00:00:21,400] Alex: you can't possibly have no feelings for her at all,
```

</details>

**第7条** `00:00:17,300 --> 00:00:18,666`

- 原始台词: `After two years of marriage,`
- 模型输出: `Alex: Alex: After two years of marriage,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
      #6 [00:00:15,266 --> 00:00:16,233] What about Sadie?
  >>> #7 [00:00:17,300 --> 00:00:18,666] After two years of marriage,
      #8 [00:00:18,666 --> 00:00:21,400] you can't possibly have no feelings for her at all,
      #9 [00:00:21,400 --> 00:00:21,766] right?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #5 [00:00:07,933 --> 00:00:09,966] Alex: Did you really spend the entire night with Kyla?
      #6 [00:00:15,266 --> 00:00:16,233] Alex: What about Sadie?
  >>> #7 [00:00:17,300 --> 00:00:18,666] Alex: After two years of marriage,
      #8 [00:00:18,666 --> 00:00:21,400] Alex: you can't possibly have no feelings for her at all,
      #9 [00:00:21,400 --> 00:00:21,766] Alex: right?
```

</details>

### 第3集（22条，展示前5条）

**第2条** `00:00:02,766 --> 00:00:03,966`

- 原始台词: `I still go to Wall Group.`
- 模型输出: `Narration: Narration: I still go to Wall Group.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:02,066 --> 00:00:02,766] Narration: The next day,
  >>> #2 [00:00:02,766 --> 00:00:03,966] I still go to Wall Group.
      #3 [00:00:04,833 --> 00:00:05,500] Back then,
      #4 [00:00:05,500 --> 00:00:07,366] I joined the company to be near Noah.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:02,066 --> 00:00:02,766] Narration: The next day,
  >>> #2 [00:00:02,766 --> 00:00:03,966] Narration: I still go to Wall Group.
      #3 [00:00:04,833 --> 00:00:05,500] Narration: Back then,
      #4 [00:00:05,500 --> 00:00:07,366] Narration: I joined the company to be near Noah.
```

</details>

**第3条** `00:00:04,833 --> 00:00:05,500`

- 原始台词: `Back then,`
- 模型输出: `Narration: Narration: Back then,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:02,066 --> 00:00:02,766] Narration: The next day,
      #2 [00:00:02,766 --> 00:00:03,966] I still go to Wall Group.
  >>> #3 [00:00:04,833 --> 00:00:05,500] Back then,
      #4 [00:00:05,500 --> 00:00:07,366] I joined the company to be near Noah.
      #5 [00:00:12,166 --> 00:00:14,000] Our marriage is hidden from most.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:02,066 --> 00:00:02,766] Narration: The next day,
      #2 [00:00:02,766 --> 00:00:03,966] Narration: I still go to Wall Group.
  >>> #3 [00:00:04,833 --> 00:00:05,500] Narration: Back then,
      #4 [00:00:05,500 --> 00:00:07,366] Narration: I joined the company to be near Noah.
      #5 [00:00:12,166 --> 00:00:14,000] Narration: Our marriage is hidden from most.
```

</details>

**第4条** `00:00:05,500 --> 00:00:07,366`

- 原始台词: `I joined the company to be near Noah.`
- 模型输出: `Narration: Narration: I joined the company to be near Noah.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:02,766 --> 00:00:03,966] I still go to Wall Group.
      #3 [00:00:04,833 --> 00:00:05,500] Back then,
  >>> #4 [00:00:05,500 --> 00:00:07,366] I joined the company to be near Noah.
      #5 [00:00:12,166 --> 00:00:14,000] Our marriage is hidden from most.
      #6 [00:00:14,400 --> 00:00:15,900] There is no luxury of rest
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:02,766 --> 00:00:03,966] Narration: I still go to Wall Group.
      #3 [00:00:04,833 --> 00:00:05,500] Narration: Back then,
  >>> #4 [00:00:05,500 --> 00:00:07,366] Narration: I joined the company to be near Noah.
      #5 [00:00:12,166 --> 00:00:14,000] Narration: Our marriage is hidden from most.
      #6 [00:00:14,400 --> 00:00:15,900] Narration: There is no luxury of rest
```

</details>

**第5条** `00:00:12,166 --> 00:00:14,000`

- 原始台词: `Our marriage is hidden from most.`
- 模型输出: `Narration: Narration: Our marriage is hidden from most.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #3 [00:00:04,833 --> 00:00:05,500] Back then,
      #4 [00:00:05,500 --> 00:00:07,366] I joined the company to be near Noah.
  >>> #5 [00:00:12,166 --> 00:00:14,000] Our marriage is hidden from most.
      #6 [00:00:14,400 --> 00:00:15,900] There is no luxury of rest
      #7 [00:00:15,900 --> 00:00:17,566] when you are raising a child alone.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #3 [00:00:04,833 --> 00:00:05,500] Narration: Back then,
      #4 [00:00:05,500 --> 00:00:07,366] Narration: I joined the company to be near Noah.
  >>> #5 [00:00:12,166 --> 00:00:14,000] Narration: Our marriage is hidden from most.
      #6 [00:00:14,400 --> 00:00:15,900] Narration: There is no luxury of rest
      #7 [00:00:15,900 --> 00:00:17,566] Narration: when you are raising a child alone.
```

</details>

**第6条** `00:00:14,400 --> 00:00:15,900`

- 原始台词: `There is no luxury of rest`
- 模型输出: `Narration: Narration: There is no luxury of rest`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #4 [00:00:05,500 --> 00:00:07,366] I joined the company to be near Noah.
      #5 [00:00:12,166 --> 00:00:14,000] Our marriage is hidden from most.
  >>> #6 [00:00:14,400 --> 00:00:15,900] There is no luxury of rest
      #7 [00:00:15,900 --> 00:00:17,566] when you are raising a child alone.
      #8 [00:00:20,466 --> 00:00:23,233] The secretarial department is buzzing with gossip.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #4 [00:00:05,500 --> 00:00:07,366] Narration: I joined the company to be near Noah.
      #5 [00:00:12,166 --> 00:00:14,000] Narration: Our marriage is hidden from most.
  >>> #6 [00:00:14,400 --> 00:00:15,900] Narration: There is no luxury of rest
      #7 [00:00:15,900 --> 00:00:17,566] Narration: when you are raising a child alone.
      #8 [00:00:20,466 --> 00:00:23,233] Narration: The secretarial department is buzzing with gossip.
```

</details>

### 第4集（20条，展示前5条）

**第2条** `00:00:00,966 --> 00:00:02,133`

- 原始台词: `I stand on the curb,`
- 模型输出: `Narration: Narration: I stand on the curb,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:00,766] Narration: After work,
  >>> #2 [00:00:00,966 --> 00:00:02,133] I stand on the curb,
      #3 [00:00:02,133 --> 00:00:03,600] trying to flag down a cab.
      #4 [00:00:04,133 --> 00:00:05,766] Noah's car stops in front of me.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:00,766] Narration: After work,
  >>> #2 [00:00:00,966 --> 00:00:02,133] Narration: I stand on the curb,
      #3 [00:00:02,133 --> 00:00:03,600] Narration: trying to flag down a cab.
      #4 [00:00:04,133 --> 00:00:05,766] Narration: Noah's car stops in front of me.
```

</details>

**第3条** `00:00:02,133 --> 00:00:03,600`

- 原始台词: `trying to flag down a cab.`
- 模型输出: `Narration: Narration: trying to flag down a cab.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:00,766] Narration: After work,
      #2 [00:00:00,966 --> 00:00:02,133] I stand on the curb,
  >>> #3 [00:00:02,133 --> 00:00:03,600] trying to flag down a cab.
      #4 [00:00:04,133 --> 00:00:05,766] Noah's car stops in front of me.
      #5 [00:00:06,266 --> 00:00:06,733] Noah: Get in.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,000 --> 00:00:00,766] Narration: After work,
      #2 [00:00:00,966 --> 00:00:02,133] Narration: I stand on the curb,
  >>> #3 [00:00:02,133 --> 00:00:03,600] Narration: trying to flag down a cab.
      #4 [00:00:04,133 --> 00:00:05,766] Narration: Noah's car stops in front of me.
      #5 [00:00:06,266 --> 00:00:06,733] Noah: Get in.
```

</details>

**第4条** `00:00:04,133 --> 00:00:05,766`

- 原始台词: `Noah's car stops in front of me.`
- 模型输出: `Narration: Narration: Noah's car stops in front of me.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:00,966 --> 00:00:02,133] I stand on the curb,
      #3 [00:00:02,133 --> 00:00:03,600] trying to flag down a cab.
  >>> #4 [00:00:04,133 --> 00:00:05,766] Noah's car stops in front of me.
      #5 [00:00:06,266 --> 00:00:06,733] Noah: Get in.
      #6 [00:00:06,733 --> 00:00:08,033] Narration: I step into the car,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:00,966 --> 00:00:02,133] Narration: I stand on the curb,
      #3 [00:00:02,133 --> 00:00:03,600] Narration: trying to flag down a cab.
  >>> #4 [00:00:04,133 --> 00:00:05,766] Narration: Noah's car stops in front of me.
      #5 [00:00:06,266 --> 00:00:06,733] Noah: Get in.
      #6 [00:00:06,733 --> 00:00:08,033] Narration: I step into the car,
```

</details>

**第7条** `00:00:08,033 --> 00:00:11,200`

- 原始台词: `and choose the back seat instead of the front.`
- 模型输出: `Narration: Narration: and choose the back seat instead of the front.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #5 [00:00:06,266 --> 00:00:06,733] Noah: Get in.
      #6 [00:00:06,733 --> 00:00:08,033] Narration: I step into the car,
  >>> #7 [00:00:08,033 --> 00:00:11,200] and choose the back seat instead of the front.
      #8 [00:00:15,533 --> 00:00:16,900] Noah: I told you I'd compensate you,
      #9 [00:00:16,900 --> 00:00:19,600] but don't think acting pitiful will make me feel sorry for you.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #5 [00:00:06,266 --> 00:00:06,733] Noah: Get in.
      #6 [00:00:06,733 --> 00:00:08,033] Narration: I step into the car,
  >>> #7 [00:00:08,033 --> 00:00:11,200] Narration: and choose the back seat instead of the front.
      #8 [00:00:15,533 --> 00:00:16,900] Noah: I told you I'd compensate you,
      #9 [00:00:16,900 --> 00:00:19,600] Noah: but don't think acting pitiful will make me feel sorry for you.
```

</details>

**第9条** `00:00:16,900 --> 00:00:19,600`

- 原始台词: `but don't think acting pitiful will make me feel sorry for you.`
- 模型输出: `Noah: Noah: but don't think acting pitiful will make me feel sorry for you.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #7 [00:00:08,033 --> 00:00:11,200] and choose the back seat instead of the front.
      #8 [00:00:15,533 --> 00:00:16,900] Noah: I told you I'd compensate you,
  >>> #9 [00:00:16,900 --> 00:00:19,600] but don't think acting pitiful will make me feel sorry for you.
      #10 [00:00:19,766 --> 00:00:20,933] Sadie: When are we getting divorced?
      #11 [00:00:20,933 --> 00:00:22,700] Noah: Relax, it's not the right time.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #7 [00:00:08,033 --> 00:00:11,200] Narration: and choose the back seat instead of the front.
      #8 [00:00:15,533 --> 00:00:16,900] Noah: I told you I'd compensate you,
  >>> #9 [00:00:16,900 --> 00:00:19,600] Noah: but don't think acting pitiful will make me feel sorry for you.
      #10 [00:00:19,766 --> 00:00:20,933] Sadie: When are we getting divorced?
      #11 [00:00:20,933 --> 00:00:22,700] Noah: Relax, it's not the right time.
```

</details>

### 第5集（21条，展示前5条）

**第4条** `00:00:16,466 --> 00:00:17,866`

- 原始台词: `do you regret marrying Noah?`
- 模型输出: `Nigel: Nigel: do you regret marrying Noah?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:06,366 --> 00:00:08,566] Noah: Then go ahead and donate your shares.
      #3 [00:00:15,966 --> 00:00:16,466] Nigel: Sadie,
  >>> #4 [00:00:16,466 --> 00:00:17,866] do you regret marrying Noah?
      #5 [00:00:19,466 --> 00:00:20,566] Sadie: No, I don't regret it.
      #6 [00:00:29,666 --> 00:00:30,866] Narration: Even though it hurts so much,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:06,366 --> 00:00:08,566] Noah: Then go ahead and donate your shares.
      #3 [00:00:15,966 --> 00:00:16,466] Nigel: Sadie,
  >>> #4 [00:00:16,466 --> 00:00:17,866] Nigel: do you regret marrying Noah?
      #5 [00:00:19,466 --> 00:00:20,566] Sadie: No, I don't regret it.
      #6 [00:00:29,666 --> 00:00:30,866] Narration: Even though it hurts so much,
```

</details>

**第7条** `00:00:30,866 --> 00:00:32,233`

- 原始台词: `I don't regret loving him.`
- 模型输出: `Narration: Narration: I don't regret loving him.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #5 [00:00:19,466 --> 00:00:20,566] Sadie: No, I don't regret it.
      #6 [00:00:29,666 --> 00:00:30,866] Narration: Even though it hurts so much,
  >>> #7 [00:00:30,866 --> 00:00:32,233] I don't regret loving him.
      #8 [00:00:32,833 --> 00:00:34,533] Nigel wants to give me shares,
      #9 [00:00:34,533 --> 00:00:35,466] but I refuse.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #5 [00:00:19,466 --> 00:00:20,566] Sadie: No, I don't regret it.
      #6 [00:00:29,666 --> 00:00:30,866] Narration: Even though it hurts so much,
  >>> #7 [00:00:30,866 --> 00:00:32,233] Narration: I don't regret loving him.
      #8 [00:00:32,833 --> 00:00:34,533] Narration: Nigel wants to give me shares,
      #9 [00:00:34,533 --> 00:00:35,466] Narration: but I refuse.
```

</details>

**第8条** `00:00:32,833 --> 00:00:34,533`

- 原始台词: `Nigel wants to give me shares,`
- 模型输出: `Narration: Narration: Nigel wants to give me shares,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #6 [00:00:29,666 --> 00:00:30,866] Narration: Even though it hurts so much,
      #7 [00:00:30,866 --> 00:00:32,233] I don't regret loving him.
  >>> #8 [00:00:32,833 --> 00:00:34,533] Nigel wants to give me shares,
      #9 [00:00:34,533 --> 00:00:35,466] but I refuse.
      #10 [00:00:38,866 --> 00:00:39,933] He can't persuade me,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #6 [00:00:29,666 --> 00:00:30,866] Narration: Even though it hurts so much,
      #7 [00:00:30,866 --> 00:00:32,233] Narration: I don't regret loving him.
  >>> #8 [00:00:32,833 --> 00:00:34,533] Narration: Nigel wants to give me shares,
      #9 [00:00:34,533 --> 00:00:35,466] Narration: but I refuse.
      #10 [00:00:38,866 --> 00:00:39,933] Narration: He can't persuade me,
```

</details>

**第9条** `00:00:34,533 --> 00:00:35,466`

- 原始台词: `but I refuse.`
- 模型输出: `Narration: Narration: but I refuse.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #7 [00:00:30,866 --> 00:00:32,233] I don't regret loving him.
      #8 [00:00:32,833 --> 00:00:34,533] Nigel wants to give me shares,
  >>> #9 [00:00:34,533 --> 00:00:35,466] but I refuse.
      #10 [00:00:38,866 --> 00:00:39,933] He can't persuade me,
      #11 [00:00:39,933 --> 00:00:41,666] so he gives me a card instead.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #7 [00:00:30,866 --> 00:00:32,233] Narration: I don't regret loving him.
      #8 [00:00:32,833 --> 00:00:34,533] Narration: Nigel wants to give me shares,
  >>> #9 [00:00:34,533 --> 00:00:35,466] Narration: but I refuse.
      #10 [00:00:38,866 --> 00:00:39,933] Narration: He can't persuade me,
      #11 [00:00:39,933 --> 00:00:41,666] Narration: so he gives me a card instead.
```

</details>

**第10条** `00:00:38,866 --> 00:00:39,933`

- 原始台词: `He can't persuade me,`
- 模型输出: `Narration: Narration: He can't persuade me,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #8 [00:00:32,833 --> 00:00:34,533] Nigel wants to give me shares,
      #9 [00:00:34,533 --> 00:00:35,466] but I refuse.
  >>> #10 [00:00:38,866 --> 00:00:39,933] He can't persuade me,
      #11 [00:00:39,933 --> 00:00:41,666] so he gives me a card instead.
      #12 [00:00:44,133 --> 00:00:45,500] After leaving the estate,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #8 [00:00:32,833 --> 00:00:34,533] Narration: Nigel wants to give me shares,
      #9 [00:00:34,533 --> 00:00:35,466] Narration: but I refuse.
  >>> #10 [00:00:38,866 --> 00:00:39,933] Narration: He can't persuade me,
      #11 [00:00:39,933 --> 00:00:41,666] Narration: so he gives me a card instead.
      #12 [00:00:44,133 --> 00:00:45,500] Narration: After leaving the estate,
```

</details>

### 第6集（19条，展示前5条）

**第2条** `00:00:01,100 --> 00:00:02,600`

- 原始台词: `I went to visit my grandmother.`
- 模型输出: `Narration: Narration: I went to visit my grandmother.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,933] Narration: On Saturday,
  >>> #2 [00:00:01,100 --> 00:00:02,600] I went to visit my grandmother.
      #3 [00:00:02,866 --> 00:00:05,400] I run into Alex outside the apartment building.
      #4 [00:00:06,566 --> 00:00:07,166] Alex: Sadie?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,933] Narration: On Saturday,
  >>> #2 [00:00:01,100 --> 00:00:02,600] Narration: I went to visit my grandmother.
      #3 [00:00:02,866 --> 00:00:05,400] Narration: I run into Alex outside the apartment building.
      #4 [00:00:06,566 --> 00:00:07,166] Alex: Sadie?
```

</details>

**第3条** `00:00:02,866 --> 00:00:05,400`

- 原始台词: `I run into Alex outside the apartment building.`
- 模型输出: `Narration: Narration: I run into Alex outside the apartment building.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,933] Narration: On Saturday,
      #2 [00:00:01,100 --> 00:00:02,600] I went to visit my grandmother.
  >>> #3 [00:00:02,866 --> 00:00:05,400] I run into Alex outside the apartment building.
      #4 [00:00:06,566 --> 00:00:07,166] Alex: Sadie?
      #5 [00:00:08,233 --> 00:00:09,000] What are you doing here?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,066 --> 00:00:00,933] Narration: On Saturday,
      #2 [00:00:01,100 --> 00:00:02,600] Narration: I went to visit my grandmother.
  >>> #3 [00:00:02,866 --> 00:00:05,400] Narration: I run into Alex outside the apartment building.
      #4 [00:00:06,566 --> 00:00:07,166] Alex: Sadie?
      #5 [00:00:08,233 --> 00:00:09,000] Alex: What are you doing here?
```

</details>

**第5条** `00:00:08,233 --> 00:00:09,000`

- 原始台词: `What are you doing here?`
- 模型输出: `Alex: Alex: What are you doing here?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #3 [00:00:02,866 --> 00:00:05,400] I run into Alex outside the apartment building.
      #4 [00:00:06,566 --> 00:00:07,166] Alex: Sadie?
  >>> #5 [00:00:08,233 --> 00:00:09,000] What are you doing here?
      #6 [00:00:10,033 --> 00:00:11,200] Sadie: My grandmother lives here.
      #7 [00:00:11,633 --> 00:00:12,333] How about you?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #3 [00:00:02,866 --> 00:00:05,400] Narration: I run into Alex outside the apartment building.
      #4 [00:00:06,566 --> 00:00:07,166] Alex: Sadie?
  >>> #5 [00:00:08,233 --> 00:00:09,000] Alex: What are you doing here?
      #6 [00:00:10,033 --> 00:00:11,200] Sadie: My grandmother lives here.
      #7 [00:00:11,633 --> 00:00:12,333] Sadie: How about you?
```

</details>

**第7条** `00:00:11,633 --> 00:00:12,333`

- 原始台词: `How about you?`
- 模型输出: `Sadie: Sadie: How about you?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #5 [00:00:08,233 --> 00:00:09,000] What are you doing here?
      #6 [00:00:10,033 --> 00:00:11,200] Sadie: My grandmother lives here.
  >>> #7 [00:00:11,633 --> 00:00:12,333] How about you?
      #8 [00:00:13,900 --> 00:00:14,866] Alex: I'm here for business.
      #9 [00:00:15,133 --> 00:00:17,166] Narration: Grandma comes out from the apartment building.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #5 [00:00:08,233 --> 00:00:09,000] Alex: What are you doing here?
      #6 [00:00:10,033 --> 00:00:11,200] Sadie: My grandmother lives here.
  >>> #7 [00:00:11,633 --> 00:00:12,333] Sadie: How about you?
      #8 [00:00:13,900 --> 00:00:14,866] Alex: I'm here for business.
      #9 [00:00:15,133 --> 00:00:17,166] Narration: Grandma comes out from the apartment building.
```

</details>

**第10条** `00:00:17,433 --> 00:00:18,833`

- 原始台词: `And when she sees Alex,`
- 模型输出: `Narration: Narration: And when she sees Alex,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #8 [00:00:13,900 --> 00:00:14,866] Alex: I'm here for business.
      #9 [00:00:15,133 --> 00:00:17,166] Narration: Grandma comes out from the apartment building.
  >>> #10 [00:00:17,433 --> 00:00:18,833] And when she sees Alex,
      #11 [00:00:19,000 --> 00:00:20,033] her eyes light up.
      #12 [00:00:22,200 --> 00:00:24,266] Grandma: Young man, what's your name?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #8 [00:00:13,900 --> 00:00:14,866] Alex: I'm here for business.
      #9 [00:00:15,133 --> 00:00:17,166] Narration: Grandma comes out from the apartment building.
  >>> #10 [00:00:17,433 --> 00:00:18,833] Narration: And when she sees Alex,
      #11 [00:00:19,000 --> 00:00:20,033] Narration: her eyes light up.
      #12 [00:00:22,200 --> 00:00:24,266] Grandma: Young man, what's your name?
```

</details>

### 第7集（13条，展示前5条）

**第6条** `00:00:14,400 --> 00:00:16,266`

- 原始台词: `I have nothing to do with him anymore.`
- 模型输出: `Narration: Narration: I have nothing to do with him anymore.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
      #5 [00:00:12,400 --> 00:00:14,100] Sadie: There's no need to explain, Alex.
  >>> #6 [00:00:14,400 --> 00:00:16,266] I have nothing to do with him anymore.
      #7 [00:00:19,600 --> 00:00:20,433] Does it hurt?
      #8 [00:00:21,233 --> 00:00:22,466] Do you need some medicine?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #4 [00:00:09,266 --> 00:00:11,800] Narration: Alex tries to explain but I stop him.
      #5 [00:00:12,400 --> 00:00:14,100] Narration: There's no need to explain, Alex.
  >>> #6 [00:00:14,400 --> 00:00:16,266] Narration: I have nothing to do with him anymore.
      #7 [00:00:19,600 --> 00:00:20,433] Narration: Does it hurt?
      #8 [00:00:21,233 --> 00:00:22,466] Narration: Do you need some medicine?
```

</details>

**第7条** `00:00:19,600 --> 00:00:20,433`

- 原始台词: `Does it hurt?`
- 模型输出: `Narration: Narration: Does it hurt?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #5 [00:00:12,400 --> 00:00:14,100] Sadie: There's no need to explain, Alex.
      #6 [00:00:14,400 --> 00:00:16,266] I have nothing to do with him anymore.
  >>> #7 [00:00:19,600 --> 00:00:20,433] Does it hurt?
      #8 [00:00:21,233 --> 00:00:22,466] Do you need some medicine?
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #5 [00:00:12,400 --> 00:00:14,100] Narration: There's no need to explain, Alex.
      #6 [00:00:14,400 --> 00:00:16,266] Narration: I have nothing to do with him anymore.
  >>> #7 [00:00:19,600 --> 00:00:20,433] Narration: Does it hurt?
      #8 [00:00:21,233 --> 00:00:22,466] Narration: Do you need some medicine?
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
```

</details>

**第8条** `00:00:21,233 --> 00:00:22,466`

- 原始台词: `Do you need some medicine?`
- 模型输出: `Narration: Narration: Do you need some medicine?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #6 [00:00:14,400 --> 00:00:16,266] I have nothing to do with him anymore.
      #7 [00:00:19,600 --> 00:00:20,433] Does it hurt?
  >>> #8 [00:00:21,233 --> 00:00:22,466] Do you need some medicine?
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
      #10 [00:00:24,200 --> 00:00:27,100] He grabs my wrist and drags me toward the elevator.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #6 [00:00:14,400 --> 00:00:16,266] Narration: I have nothing to do with him anymore.
      #7 [00:00:19,600 --> 00:00:20,433] Narration: Does it hurt?
  >>> #8 [00:00:21,233 --> 00:00:22,466] Narration: Do you need some medicine?
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
      #10 [00:00:24,200 --> 00:00:27,100] Narration: He grabs my wrist and drags me toward the elevator.
```

</details>

**第10条** `00:00:24,200 --> 00:00:27,100`

- 原始台词: `He grabs my wrist and drags me toward the elevator.`
- 模型输出: `Narration: Narration: He grabs my wrist and drags me toward the elevator.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #8 [00:00:21,233 --> 00:00:22,466] Do you need some medicine?
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
  >>> #10 [00:00:24,200 --> 00:00:27,100] He grabs my wrist and drags me toward the elevator.
      #11 [00:00:28,333 --> 00:00:29,351] Sadie: What are you doing?
      #12 [00:00:29,491 --> 00:00:30,217] Let me go!
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #8 [00:00:21,233 --> 00:00:22,466] Narration: Do you need some medicine?
      #9 [00:00:22,566 --> 00:00:24,033] Narration: Noah's anger flares up.
  >>> #10 [00:00:24,200 --> 00:00:27,100] Narration: He grabs my wrist and drags me toward the elevator.
      #11 [00:00:28,333 --> 00:00:29,351] Narration: What are you doing?
      #12 [00:00:29,491 --> 00:00:30,217] Narration: Let me go!
```

</details>

**第12条** `00:00:29,491 --> 00:00:30,217`

- 原始台词: `Let me go!`
- 模型输出: `Narration: Narration: Let me go!`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #10 [00:00:24,200 --> 00:00:27,100] He grabs my wrist and drags me toward the elevator.
      #11 [00:00:28,333 --> 00:00:29,351] Sadie: What are you doing?
  >>> #12 [00:00:29,491 --> 00:00:30,217] Let me go!
      #13 [00:00:30,366 --> 00:00:32,289] Narration: He drags me to my apartment door,
      #14 [00:00:32,289 --> 00:00:33,083] and kicks it open.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #10 [00:00:24,200 --> 00:00:27,100] Narration: He grabs my wrist and drags me toward the elevator.
      #11 [00:00:28,333 --> 00:00:29,351] Narration: What are you doing?
  >>> #12 [00:00:29,491 --> 00:00:30,217] Narration: Let me go!
      #13 [00:00:30,366 --> 00:00:32,289] Narration: He drags me to my apartment door,
      #14 [00:00:32,289 --> 00:00:33,083] Narration: and kicks it open.
```

</details>

### 第8集（32条，展示前5条）

**第2条** `00:00:03,233 --> 00:00:04,333`

- 原始台词: `I push him away.`
- 模型输出: `Narration: Narration: I push him away.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:00,233 --> 00:00:02,033] Narration: He lowers his head and kisses me.
  >>> #2 [00:00:03,233 --> 00:00:04,333] I push him away.
      #3 [00:00:04,633 --> 00:00:06,500] Sadie: Noah, come to your senses!
      #4 [00:00:07,333 --> 00:00:08,333] You love Kyla.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:00,233 --> 00:00:02,033] Narration: He lowers his head and kisses me.
  >>> #2 [00:00:03,233 --> 00:00:04,333] Narration: I push him away.
      #3 [00:00:04,633 --> 00:00:06,500] Sadie: Noah, come to your senses!
      #4 [00:00:07,333 --> 00:00:08,333] Sadie: You love Kyla.
```

</details>

**第4条** `00:00:07,333 --> 00:00:08,333`

- 原始台词: `You love Kyla.`
- 模型输出: `Sadie: Sadie: You love Kyla.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:03,233 --> 00:00:04,333] I push him away.
      #3 [00:00:04,633 --> 00:00:06,500] Sadie: Noah, come to your senses!
  >>> #4 [00:00:07,333 --> 00:00:08,333] You love Kyla.
      #5 [00:00:09,400 --> 00:00:11,466] She's back, and yet here you are.
      #6 [00:00:13,600 --> 00:00:14,866] What do you take me for?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:03,233 --> 00:00:04,333] Narration: I push him away.
      #3 [00:00:04,633 --> 00:00:06,500] Sadie: Noah, come to your senses!
  >>> #4 [00:00:07,333 --> 00:00:08,333] Sadie: You love Kyla.
      #5 [00:00:09,400 --> 00:00:11,466] Sadie: She's back, and yet here you are.
      #6 [00:00:13,600 --> 00:00:14,866] Sadie: What do you take me for?
```

</details>

**第5条** `00:00:09,400 --> 00:00:11,466`

- 原始台词: `She's back, and yet here you are.`
- 模型输出: `Sadie: Sadie: She's back, and yet here you are.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #3 [00:00:04,633 --> 00:00:06,500] Sadie: Noah, come to your senses!
      #4 [00:00:07,333 --> 00:00:08,333] You love Kyla.
  >>> #5 [00:00:09,400 --> 00:00:11,466] She's back, and yet here you are.
      #6 [00:00:13,600 --> 00:00:14,866] What do you take me for?
      #7 [00:00:16,100 --> 00:00:18,100] Noah, I've loved you for ten years!
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #3 [00:00:04,633 --> 00:00:06,500] Sadie: Noah, come to your senses!
      #4 [00:00:07,333 --> 00:00:08,333] Sadie: You love Kyla.
  >>> #5 [00:00:09,400 --> 00:00:11,466] Sadie: She's back, and yet here you are.
      #6 [00:00:13,600 --> 00:00:14,866] Sadie: What do you take me for?
      #7 [00:00:16,100 --> 00:00:18,100] Sadie: Noah, I've loved you for ten years!
```

</details>

**第6条** `00:00:13,600 --> 00:00:14,866`

- 原始台词: `What do you take me for?`
- 模型输出: `Sadie: Sadie: What do you take me for?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #4 [00:00:07,333 --> 00:00:08,333] You love Kyla.
      #5 [00:00:09,400 --> 00:00:11,466] She's back, and yet here you are.
  >>> #6 [00:00:13,600 --> 00:00:14,866] What do you take me for?
      #7 [00:00:16,100 --> 00:00:18,100] Noah, I've loved you for ten years!
      #8 [00:00:18,700 --> 00:00:20,633] Yet, I've never had a place in your heart.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #4 [00:00:07,333 --> 00:00:08,333] Sadie: You love Kyla.
      #5 [00:00:09,400 --> 00:00:11,466] Sadie: She's back, and yet here you are.
  >>> #6 [00:00:13,600 --> 00:00:14,866] Sadie: What do you take me for?
      #7 [00:00:16,100 --> 00:00:18,100] Sadie: Noah, I've loved you for ten years!
      #8 [00:00:18,700 --> 00:00:20,633] Sadie: Yet, I've never had a place in your heart.
```

</details>

**第7条** `00:00:16,100 --> 00:00:18,100`

- 原始台词: `Noah, I've loved you for ten years!`
- 模型输出: `Sadie: Sadie: Noah, I've loved you for ten years!`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #5 [00:00:09,400 --> 00:00:11,466] She's back, and yet here you are.
      #6 [00:00:13,600 --> 00:00:14,866] What do you take me for?
  >>> #7 [00:00:16,100 --> 00:00:18,100] Noah, I've loved you for ten years!
      #8 [00:00:18,700 --> 00:00:20,633] Yet, I've never had a place in your heart.
      #9 [00:00:21,233 --> 00:00:22,633] I know I can't demand your love,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #5 [00:00:09,400 --> 00:00:11,466] Sadie: She's back, and yet here you are.
      #6 [00:00:13,600 --> 00:00:14,866] Sadie: What do you take me for?
  >>> #7 [00:00:16,100 --> 00:00:18,100] Sadie: Noah, I've loved you for ten years!
      #8 [00:00:18,700 --> 00:00:20,633] Sadie: Yet, I've never had a place in your heart.
      #9 [00:00:21,233 --> 00:00:22,633] Sadie: I know I can't demand your love,
```

</details>

### 第9集（21条，展示前5条）

**第4条** `00:00:06,866 --> 00:00:07,900`

- 原始台词: `but funny thing,`
- 模型输出: `Narration: Narration: but funny thing,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:03,800 --> 00:00:04,833] Sadie: Was it you?
      #3 [00:00:04,900 --> 00:00:06,866] Kyla: I heard you've loved Noah for ten years,
  >>> #4 [00:00:06,866 --> 00:00:07,900] but funny thing,
      #5 [00:00:08,266 --> 00:00:10,200] he's loved me for just as long.
      #6 [00:00:10,200 --> 00:00:11,100] So tell me,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:03,800 --> 00:00:04,833] Narration: Was it you?
      #3 [00:00:04,900 --> 00:00:06,866] Narration: I heard you've loved Noah for ten years,
  >>> #4 [00:00:06,866 --> 00:00:07,900] Narration: but funny thing,
      #5 [00:00:08,266 --> 00:00:10,200] Narration: he's loved me for just as long.
      #6 [00:00:10,200 --> 00:00:11,100] Narration: So tell me,
```

</details>

**第5条** `00:00:08,266 --> 00:00:10,200`

- 原始台词: `he's loved me for just as long.`
- 模型输出: `Narration: Narration: he's loved me for just as long.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #3 [00:00:04,900 --> 00:00:06,866] Kyla: I heard you've loved Noah for ten years,
      #4 [00:00:06,866 --> 00:00:07,900] but funny thing,
  >>> #5 [00:00:08,266 --> 00:00:10,200] he's loved me for just as long.
      #6 [00:00:10,200 --> 00:00:11,100] So tell me,
      #7 [00:00:11,100 --> 00:00:12,733] do you think he'll make your marriage public,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #3 [00:00:04,900 --> 00:00:06,866] Narration: I heard you've loved Noah for ten years,
      #4 [00:00:06,866 --> 00:00:07,900] Narration: but funny thing,
  >>> #5 [00:00:08,266 --> 00:00:10,200] Narration: he's loved me for just as long.
      #6 [00:00:10,200 --> 00:00:11,100] Narration: So tell me,
      #7 [00:00:11,100 --> 00:00:12,733] Narration: do you think he'll make your marriage public,
```

</details>

**第6条** `00:00:10,200 --> 00:00:11,100`

- 原始台词: `So tell me,`
- 模型输出: `Narration: Narration: So tell me,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #4 [00:00:06,866 --> 00:00:07,900] but funny thing,
      #5 [00:00:08,266 --> 00:00:10,200] he's loved me for just as long.
  >>> #6 [00:00:10,200 --> 00:00:11,100] So tell me,
      #7 [00:00:11,100 --> 00:00:12,733] do you think he'll make your marriage public,
      #8 [00:00:12,733 --> 00:00:14,066] or will he just discard you?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #4 [00:00:06,866 --> 00:00:07,900] Narration: but funny thing,
      #5 [00:00:08,266 --> 00:00:10,200] Narration: he's loved me for just as long.
  >>> #6 [00:00:10,200 --> 00:00:11,100] Narration: So tell me,
      #7 [00:00:11,100 --> 00:00:12,733] Narration: do you think he'll make your marriage public,
      #8 [00:00:12,733 --> 00:00:14,066] Narration: or will he just discard you?
```

</details>

**第7条** `00:00:11,100 --> 00:00:12,733`

- 原始台词: `do you think he'll make your marriage public,`
- 模型输出: `Narration: Narration: do you think he'll make your marriage public,`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #5 [00:00:08,266 --> 00:00:10,200] he's loved me for just as long.
      #6 [00:00:10,200 --> 00:00:11,100] So tell me,
  >>> #7 [00:00:11,100 --> 00:00:12,733] do you think he'll make your marriage public,
      #8 [00:00:12,733 --> 00:00:14,066] or will he just discard you?
      #9 [00:00:14,800 --> 00:00:16,866] Sadie: Are you so certain he'll choose you?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #5 [00:00:08,266 --> 00:00:10,200] Narration: he's loved me for just as long.
      #6 [00:00:10,200 --> 00:00:11,100] Narration: So tell me,
  >>> #7 [00:00:11,100 --> 00:00:12,733] Narration: do you think he'll make your marriage public,
      #8 [00:00:12,733 --> 00:00:14,066] Narration: or will he just discard you?
      #9 [00:00:14,800 --> 00:00:16,866] Narration: Are you so certain he'll choose you?
```

</details>

**第8条** `00:00:12,733 --> 00:00:14,066`

- 原始台词: `or will he just discard you?`
- 模型输出: `Narration: Narration: or will he just discard you?`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #6 [00:00:10,200 --> 00:00:11,100] So tell me,
      #7 [00:00:11,100 --> 00:00:12,733] do you think he'll make your marriage public,
  >>> #8 [00:00:12,733 --> 00:00:14,066] or will he just discard you?
      #9 [00:00:14,800 --> 00:00:16,866] Sadie: Are you so certain he'll choose you?
      #10 [00:00:19,266 --> 00:00:21,333] I've shared his bed for two years.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #6 [00:00:10,200 --> 00:00:11,100] Narration: So tell me,
      #7 [00:00:11,100 --> 00:00:12,733] Narration: do you think he'll make your marriage public,
  >>> #8 [00:00:12,733 --> 00:00:14,066] Narration: or will he just discard you?
      #9 [00:00:14,800 --> 00:00:16,866] Narration: Are you so certain he'll choose you?
      #10 [00:00:19,266 --> 00:00:21,333] Narration: I've shared his bed for two years.
```

</details>

### 第10集（14条，展示前5条）

**第2条** `00:00:05,600 --> 00:00:06,433`

- 原始台词: `Noah calls.`
- 模型输出: `Narration: Narration: Noah calls.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #1 [00:00:02,300 --> 00:00:05,466] Narration: I get into a taxi, wanting to go back to my apartment.
  >>> #2 [00:00:05,600 --> 00:00:06,433] Noah calls.
      #3 [00:00:10,366 --> 00:00:11,400] Noah: Sadie, where are you?
      #4 [00:00:11,433 --> 00:00:12,433] Get back here right now
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #1 [00:00:02,300 --> 00:00:05,466] Narration: I get into a taxi, wanting to go back to my apartment.
  >>> #2 [00:00:05,600 --> 00:00:06,433] Narration: Noah calls.
      #3 [00:00:10,366 --> 00:00:11,400] Noah: Sadie, where are you?
      #4 [00:00:11,433 --> 00:00:12,433] Noah: Get back here right now
```

</details>

**第4条** `00:00:11,433 --> 00:00:12,433`

- 原始台词: `Get back here right now`
- 模型输出: `Noah: Noah: Get back here right now`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #2 [00:00:05,600 --> 00:00:06,433] Noah calls.
      #3 [00:00:10,366 --> 00:00:11,400] Noah: Sadie, where are you?
  >>> #4 [00:00:11,433 --> 00:00:12,433] Get back here right now
      #5 [00:00:12,433 --> 00:00:13,233] we're going to the hospital!
      #6 [00:00:16,500 --> 00:00:17,666] Sadie: Are you worried about me?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #2 [00:00:05,600 --> 00:00:06,433] Narration: Noah calls.
      #3 [00:00:10,366 --> 00:00:11,400] Noah: Sadie, where are you?
  >>> #4 [00:00:11,433 --> 00:00:12,433] Noah: Get back here right now
      #5 [00:00:12,433 --> 00:00:13,233] Noah: we're going to the hospital!
      #6 [00:00:16,500 --> 00:00:17,666] Sadie: Are you worried about me?
```

</details>

**第5条** `00:00:12,433 --> 00:00:13,233`

- 原始台词: `we're going to the hospital!`
- 模型输出: `Noah: Noah: we're going to the hospital!`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #3 [00:00:10,366 --> 00:00:11,400] Noah: Sadie, where are you?
      #4 [00:00:11,433 --> 00:00:12,433] Get back here right now
  >>> #5 [00:00:12,433 --> 00:00:13,233] we're going to the hospital!
      #6 [00:00:16,500 --> 00:00:17,666] Sadie: Are you worried about me?
      #7 [00:00:18,433 --> 00:00:18,833] Kyla: Noah,
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #3 [00:00:10,366 --> 00:00:11,400] Noah: Sadie, where are you?
      #4 [00:00:11,433 --> 00:00:12,433] Noah: Get back here right now
  >>> #5 [00:00:12,433 --> 00:00:13,233] Noah: we're going to the hospital!
      #6 [00:00:16,500 --> 00:00:17,666] Sadie: Are you worried about me?
      #7 [00:00:18,433 --> 00:00:18,833] Kyla: Noah,
```

</details>

**第8条** `00:00:18,900 --> 00:00:20,366`

- 原始台词: `my friends are hosting a welcome party`
- 模型输出: `Kyla: Kyla: my friends are hosting a welcome party`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #6 [00:00:16,500 --> 00:00:17,666] Sadie: Are you worried about me?
      #7 [00:00:18,433 --> 00:00:18,833] Kyla: Noah,
  >>> #8 [00:00:18,900 --> 00:00:20,366] my friends are hosting a welcome party
      #9 [00:00:20,366 --> 00:00:21,033] for me tonight.
      #10 [00:00:21,100 --> 00:00:22,000] Could you come with me?
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #6 [00:00:16,500 --> 00:00:17,666] Sadie: Are you worried about me?
      #7 [00:00:18,433 --> 00:00:18,833] Kyla: Noah,
  >>> #8 [00:00:18,900 --> 00:00:20,366] Kyla: my friends are hosting a welcome party
      #9 [00:00:20,366 --> 00:00:21,033] Kyla: for me tonight.
      #10 [00:00:21,100 --> 00:00:22,000] Kyla: Could you come with me?
```

</details>

**第9条** `00:00:20,366 --> 00:00:21,033`

- 原始台词: `for me tonight.`
- 模型输出: `Kyla: Kyla: for me tonight.`

<details>
<summary>📋 原始剧本上下文</summary>

```
      #7 [00:00:18,433 --> 00:00:18,833] Kyla: Noah,
      #8 [00:00:18,900 --> 00:00:20,366] my friends are hosting a welcome party
  >>> #9 [00:00:20,366 --> 00:00:21,033] for me tonight.
      #10 [00:00:21,100 --> 00:00:22,000] Could you come with me?
      #11 [00:00:22,566 --> 00:00:24,266] Narration: A vice tightens around my heart.
```

</details>

<details>
<summary>📋 模型输出上下文</summary>

```
      #7 [00:00:18,433 --> 00:00:18,833] Kyla: Noah,
      #8 [00:00:18,900 --> 00:00:20,366] Kyla: my friends are hosting a welcome party
  >>> #9 [00:00:20,366 --> 00:00:21,033] Kyla: for me tonight.
      #10 [00:00:21,100 --> 00:00:22,000] Kyla: Could you come with me?
      #11 [00:00:22,566 --> 00:00:24,266] Narration: A vice tightens around my heart.
```

</details>


## 7. 数据缺口

| 系统 | 状态 | 需补充数据 |
| --- | --- | --- |
| XEY5 60集之后 | ⚠ 仅有1-10集 | 第60-100集模型输出SRT |
| XEY121 | ⚠ 无数据 | 至少7集原始SRT + 下载人名字幕 |
| XEY118 | ⚠ 无数据 | 原始SRT + 下载人名字幕 |

## 8. 版本演进历史

| 版本 | 时间 | 错标 | 新增Narration | 正确保留率 | 主要变化 |
| --- | --- | ---: | ---: | ---: | --- |
| v1 | 7/30 初版 | 2 | 9 | 69.1% | 初始比对，仅关注漏标场景 |
| v2 | 7/30 修订 | 22 | 186 | 77.3% | 自动化脚本，发现全部10集不通过 |
| v3 | 7/31 10:21 | 22 | 185 | 77.3% | 第4/5集错标修复，第2/3集退化 |
| v4 | 7/31 11:03 | 18 | 178 | 81.4% | 第2/3/8/10集错标全修复，第7/9集退化 |
| v5 | 7/31 11:30 | 18 | 225 | 81.4% | 错标持平，新增Narration反弹 +47 |
| v6 | 7/31 14:22 | 18 | 225 | 81.4% | 与v5一致，无变化 |

### 趋势分析

```
错标数量:  22 → 22 → 18 → 18 → 18  (稳定在18)
新增标注: 186 → 185 → 178 → 225 → 225 (反弹后持平)
正确保留: 77.3% → 77.3% → 81.4% → 81.4% → 81.4% (稳定)
```

- ✅ **错标稳定**：18条集中在第7/9集，其余8集已全部修复
- ⚠ **新增Narration反弹后持平**：225条，v5→v6无变化
- ❌ **核心瓶颈**：无依据新增Narration仍是最大问题