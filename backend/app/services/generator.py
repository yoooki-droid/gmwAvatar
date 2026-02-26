import base64
import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request

from html import escape
from typing import Any

import httpx
from openai import AzureOpenAI

from ..config import settings


QUESTION_PERSONA_PROMPTS: dict[str, str] = {
    "board_director": "你是董事会独立董事，风格犀利，强调问责、决策质量与风险边界。",
    "cro": "你是首席风险官，关注风险识别、触发条件、缓释预案与底线。",
    "coo": "你是首席运营官，关注执行闭环、资源效率、跨部门协同与里程碑。",
    "cfo": "你是首席财务官，关注预算纪律、现金流、ROI 与财务可持续性。",
    "strategy": "你是战略顾问，关注战略一致性、优先级取舍与长期竞争力。",
}


def normalize_question_persona(persona_key: str | None) -> str:
    key = str(persona_key or "").strip().lower()
    if key in QUESTION_PERSONA_PROMPTS:
        return key
    return "board_director"


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？!?\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_json_text(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text.startswith("{") and text.endswith("}"):
        return text
    match = re.search(r"\{[\s\S]*\}", text)
    return match.group(0) if match else ""


def _build_client() -> AzureOpenAI:
    if not settings.azure_openai_api_key:
        raise ValueError("未配置 Azure AI 参数，请先配置 AZURE_OPENAI_API_KEY")

    endpoint = (settings.azure_endpoint_url or "").strip()
    base_url = (settings.azure_base_url or "").strip()
    if not endpoint and not base_url:
        raise ValueError(
            "未配置 Azure AI 地址，请配置 AZURE_ENDPOINT_URL 或 AZURE_BASE_URL"
        )

    http_client = httpx.Client(
        verify=not settings.azure_ssl_skip_verify,
        timeout=settings.azure_request_timeout_sec,
    )
    # 优先使用 Azure 原生 endpoint；base_url 仅作为后备兼容。
    if endpoint:
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_api_version,
            http_client=http_client,
            max_retries=0,
        )

    return AzureOpenAI(
        base_url=base_url,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_api_version,
        http_client=http_client,
        max_retries=0,
    )


def _chat_completion_with_retry(client: AzureOpenAI, **kwargs):
    retries = max(1, int(settings.azure_request_retry_count))
    backoff = max(0.2, float(settings.azure_request_retry_backoff_sec))
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return client.chat.completions.create(
                **kwargs,
                timeout=settings.azure_request_timeout_sec,
            )
        except Exception as exc:
            last_error = exc
            if attempt >= retries:
                break
            # 网络抖动时做指数退避重试。
            sleep_sec = backoff * (2 ** (attempt - 1))
            time.sleep(min(8.0, sleep_sec))
    raise ValueError(f"AI 请求失败（重试 {retries} 次后仍失败）: {last_error}")


def _chat_completion_with_model_fallback(client: AzureOpenAI, **kwargs):
    fallback_models = [
        x.strip()
        for x in (settings.azure_deployment_fallbacks or "").split(",")
        if x.strip()
    ]
    model_candidates: list[str] = []
    for model_name in [settings.azure_deployment_name, *fallback_models]:
        if model_name and model_name not in model_candidates:
            model_candidates.append(model_name)

    last_error: Exception | None = None
    for model_name in model_candidates:
        try:
            return _chat_completion_with_retry(client, model=model_name, **kwargs)
        except Exception as exc:
            last_error = exc
            text = str(exc)
            # 仅在部署不存在时继续尝试下一个部署，其他错误直接抛出。
            if (
                ("Resource not found" in text)
                or ("'code': '404'" in text)
                or ("Error code: 404" in text)
            ):
                continue
            raise

    raise ValueError(
        f"AI 请求失败：可用部署均不可用（{','.join(model_candidates)}），最后错误: {last_error}"
    )


def _completion_text(completion: Any) -> str:
    # 兼容 Azure/OpenAI SDK 多种返回结构，避免因响应结构差异导致解析失败。
    if completion is None:
        return ""
    if isinstance(completion, str):
        return completion.strip()

    if isinstance(completion, dict):
        choices = (
            completion.get("choices")
            if isinstance(completion.get("choices"), list)
            else []
        )
        if choices:
            first = choices[0] if isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first, dict) else {}
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = [
                    str(x.get("text") or "") for x in content if isinstance(x, dict)
                ]
                return "".join(parts).strip()
        output_text = completion.get("output_text")
        if isinstance(output_text, str):
            return output_text.strip()
        if isinstance(output_text, list):
            return "".join(str(x) for x in output_text).strip()
        return json.dumps(completion, ensure_ascii=False)

    try:
        choices = getattr(completion, "choices", None)
        if choices and len(choices) > 0:
            first = choices[0]
            message = getattr(first, "message", None)
            content = getattr(message, "content", None) if message is not None else None
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = []
                for item in content:
                    text_value = (
                        getattr(item, "text", None) if item is not None else None
                    )
                    if isinstance(item, dict):
                        text_value = item.get("text")
                    if text_value:
                        parts.append(str(text_value))
                return "".join(parts).strip()
        output_text = getattr(completion, "output_text", None)
        if isinstance(output_text, str):
            return output_text.strip()
        if isinstance(output_text, list):
            return "".join(str(x) for x in output_text).strip()
        if hasattr(completion, "model_dump"):
            dumped = completion.model_dump()
            return _completion_text(dumped)
    except Exception:
        pass
    return str(completion).strip()


def _response_to_bytes(response: Any) -> bytes:
    if response is None:
        return b""
    if isinstance(response, (bytes, bytearray)):
        return bytes(response)
    if hasattr(response, "read"):
        try:
            data = response.read()
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        except Exception:
            pass
    if hasattr(response, "content"):
        data = response.content
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
    if hasattr(response, "to_bytes"):
        try:
            data = response.to_bytes()
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        except Exception:
            pass
    return b""


def _extract_wav_pcm_data(audio_bytes: bytes) -> bytes:
    # 兼容模型返回 wav 的情况，尽量抽取 data chunk 作为 PCM。
    if (
        len(audio_bytes) < 44
        or audio_bytes[:4] != b"RIFF"
        or audio_bytes[8:12] != b"WAVE"
    ):
        return audio_bytes
    offset = 12
    total = len(audio_bytes)
    while offset + 8 <= total:
        chunk_id = audio_bytes[offset : offset + 4]
        chunk_size = int.from_bytes(
            audio_bytes[offset + 4 : offset + 8], "little", signed=False
        )
        chunk_start = offset + 8
        chunk_end = chunk_start + chunk_size
        if chunk_end > total:
            break
        if chunk_id == b"data":
            return audio_bytes[chunk_start:chunk_end]
        offset = chunk_end + (chunk_size % 2)
    return audio_bytes


def _resolve_speech_tts_endpoint() -> str:
    endpoint = (settings.azure_speech_endpoint or "").strip()
    tts_path = (
        settings.azure_speech_tts_path or "/tts/cognitiveservices/v1"
    ).strip() or "/tts/cognitiveservices/v1"
    if endpoint:
        base = endpoint.rstrip("/")
        if base.endswith("/tts/cognitiveservices/v1"):
            return base
        if not tts_path.startswith("/"):
            tts_path = f"/{tts_path}"
        return f"{base}{tts_path}"
    region = (settings.azure_speech_region or "").strip()
    if not region:
        return ""
    return f"https://{region}.api.cognitive.microsoft.com/tts/cognitiveservices/v1"


def _resolve_speech_voice(language_key: str) -> tuple[str, str]:
    # 使用 Azure Speech 官方 Neural Voice，优先保证各语种发音自然度。
    voice_map = {
        "zh": ("zh-CN", "zh-CN-XiaoxiaoNeural"),
        "en": ("en-US", "en-US-JennyNeural"),
        "yue": ("zh-HK", "zh-HK-HiuGaaiNeural"),
        "ja": ("ja-JP", "ja-JP-NanamiNeural"),
        "id": ("id-ID", "id-ID-GadisNeural"),
        "ms": ("ms-MY", "ms-MY-YasminNeural"),
        "hi": ("hi-IN", "hi-IN-SwaraNeural"),
    }
    return voice_map.get(language_key, ("en-US", "en-US-JennyNeural"))


def _synthesize_with_azure_speech_service(
    script_text: str, language_key: str, language_label: str
) -> str:
    key = (settings.azure_speech_key or "").strip()
    key2 = (settings.azure_speech_key_secondary or "").strip()
    endpoint = _resolve_speech_tts_endpoint()
    if not key or not endpoint:
        raise ValueError(
            "未配置 Azure Speech 参数，请先配置 AZURE_SPEECH_KEY 与 AZURE_SPEECH_ENDPOINT/AZURE_SPEECH_REGION"
        )

    xml_lang, voice_name = _resolve_speech_voice(language_key)
    ssml = (
        f"<speak version='1.0' xml:lang='{xml_lang}'>"
        f"<voice xml:lang='{xml_lang}' name='{voice_name}'>{escape(script_text)}</voice>"
        "</speak>"
    )
    body = ssml.encode("utf-8")
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": settings.azure_speech_output_format,
        "User-Agent": "gmwAvatar",
    }

    def _call_once(sub_key: str) -> bytes:
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={**headers, "Ocp-Apim-Subscription-Key": sub_key},
            method="POST",
        )
        if settings.azure_ssl_skip_verify:
            context = ssl._create_unverified_context()
        else:
            context = ssl.create_default_context()
        with urllib.request.urlopen(
            req, timeout=settings.azure_request_timeout_sec, context=context
        ) as resp:
            return resp.read()

    try:
        audio_bytes = _call_once(key)
    except urllib.error.HTTPError as exc:
        # 主 key 失败时自动切换 key2。
        if key2 and exc.code in (401, 403, 429):
            try:
                audio_bytes = _call_once(key2)
            except Exception as exc2:
                raise ValueError(
                    f"Azure Speech 合成失败({language_key}/{language_label}): {exc2}"
                ) from exc2
        else:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(
                f"Azure Speech 合成失败({language_key}/{language_label}): HTTP {exc.code} {detail}"
            ) from exc
    except Exception as exc:
        raise ValueError(
            f"Azure Speech 合成失败({language_key}/{language_label}): {exc}"
        ) from exc

    if not audio_bytes:
        raise ValueError(f"Azure Speech 合成结果为空({language_key}/{language_label})")
    return base64.b64encode(audio_bytes).decode("ascii")


def generate_finance_reflections(
    title_text: str, summary_text: str, script_text: str
) -> list[str]:
    title = title_text.strip()
    summary = summary_text.strip()
    script = script_text.strip()
    source_text = script or summary
    if not source_text:
        raise ValueError("会议内容不能为空")

    client = _build_client()
    prompt = (
        "你是国际金融与公司治理专家，擅长投融资、财务分析、全球金融市场。"
        "请基于会议内容给出 3 到 5 条“反思建议”，每条建议要可执行、可落地。"
        "反思方向必须覆盖：公司治理、财务健康、全球金融环境影响（可交叉组合）。"
        '严格返回 JSON：{"reflections":["建议1","建议2","建议3"]}'
        "只返回 JSON，不要其他文字。"
    )
    try:
        completion = _chat_completion_with_model_fallback(
            client,
            messages=[
                {"role": "system", "content": [{"type": "text", "text": prompt}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {"title": title, "summary": summary, "script": script},
                                ensure_ascii=False,
                            ),
                        }
                    ],
                },
            ],
            max_completion_tokens=1800,
            stream=False,
        )
        content = _completion_text(completion)
        json_text = _extract_json_text(content)
        if not json_text:
            raise ValueError("AI 返回格式异常，未解析到 JSON")
        parsed = json.loads(json_text)
        raw = parsed.get("reflections", [])
        if not isinstance(raw, list):
            raw = []
        reflections = [str(x).replace("```", "").strip() for x in raw if str(x).strip()]
        reflections = reflections[:5]
        if len(reflections) >= 3:
            return reflections
    except Exception:
        # 回退：保证流程可用。
        pass

    fallback = [
        "从公司治理看，建议明确决策链路与问责机制，避免跨部门推进中责任边界模糊。",
        "从财务角度看，建议先量化投入产出与现金流影响，设置分阶段预算闸口。",
        "从全球金融环境看，建议评估汇率、利率与外部需求波动对目标达成的影响。",
    ]
    return fallback


def generate_sharp_questions(
    title_text: str,
    summary_text: str,
    script_text: str,
    persona_key: str = "board_director",
) -> list[str]:
    title = title_text.strip()
    summary = summary_text.strip()
    script = script_text.strip()
    source_text = script or summary
    if not source_text:
        raise ValueError("会议内容不能为空")

    persona = normalize_question_persona(persona_key)
    persona_prompt = QUESTION_PERSONA_PROMPTS[persona]

    client = _build_client()
    prompt = (
        f"{persona_prompt}"
        "请基于输入会议内容提出 1 到 3 条“犀利问题”。"
        "问题必须聚焦会议内容本身，不能泛泛而谈，不能包含答案。"
        "每条问题控制在 16 到 38 个汉字左右，避免重复。"
        '严格返回 JSON：{"questions":["问题1","问题2"]}'
        "只返回 JSON，不要其他文字。"
    )
    user_payload = {
        "title": title,
        "summary": summary,
        "script": script,
        "persona": persona,
    }

    try:
        completion = _chat_completion_with_model_fallback(
            client,
            messages=[
                {"role": "system", "content": [{"type": "text", "text": prompt}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(user_payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            max_completion_tokens=1400,
            stream=False,
        )
        content = _completion_text(completion)
        json_text = _extract_json_text(content)
        if not json_text:
            raise ValueError("AI 返回格式异常，未解析到 JSON")
        parsed = json.loads(json_text)
        raw = parsed.get("questions", [])
        if not isinstance(raw, list):
            raw = []
        questions = [str(x).replace("```", "").strip() for x in raw if str(x).strip()][
            :3
        ]
        if questions:
            return questions
    except Exception:
        pass

    sentences = _split_sentences(source_text)
    anchor = sentences[0] if sentences else "本次会议的关键目标"
    fallback = [
        f"围绕“{anchor}”，本次会议给出的最晚交付节点到底是什么？",
        "如果核心假设被证伪，团队是否有可立即执行的替代方案？",
        "谁对最终结果负全责，验收标准和问责机制是否已经写清？",
    ]
    return fallback[:3]


def generate_script_and_highlights(
    summary_raw: str,
    speaker: str,
    title: str = "",
    question_persona: str = "board_director",
) -> tuple[str, list[str], list[str], list[str]]:
    if not summary_raw.strip():
        raise ValueError("内容不能为空")
    client = _build_client()
    prompt = (
        "你是新闻口播编辑，同时具备国际金融与财务分析背景。"
        "请将会议总结改写为通俗口播稿，并提取2条亮点，同时给出3到5条金融专家反思建议和1到3条犀利提问。"
        "反思建议要覆盖公司治理、财务、全球金融等角度，内容具体可执行。"
        f"提问视角采用人设：{normalize_question_persona(question_persona)}。提问必须只包含问题，不要答案。"
        "必须严格返回 JSON，不要输出任何额外文字。"
        '格式为：{"script":"...","highlights":["...","..."],"reflections":["...","...","..."],"questions":["...","..."]}'
    )
    try:
        completion = _chat_completion_with_model_fallback(
            client,
            messages=[
                {"role": "system", "content": [{"type": "text", "text": prompt}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"新闻标题：{title}\n发言人：{speaker}\n会议总结：{summary_raw}",
                        }
                    ],
                },
            ],
            max_completion_tokens=1200,
            stream=False,
        )

        content = _completion_text(completion)
        json_text = _extract_json_text(content)
        if not json_text:
            raise ValueError("AI 返回格式异常，未解析到 JSON")
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI 返回 JSON 解析失败: {exc}") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"AI 调用失败: {exc}") from exc

    script = str(parsed.get("script", "")).strip()
    highlights_raw = parsed.get("highlights", [])
    if not isinstance(highlights_raw, list):
        highlights_raw = []
    highlights = [str(x).strip() for x in highlights_raw if str(x).strip()][:2]
    reflections_raw = parsed.get("reflections", [])
    if not isinstance(reflections_raw, list):
        reflections_raw = []
    reflections = [str(x).strip() for x in reflections_raw if str(x).strip()][:5]
    questions_raw = parsed.get("questions", [])
    if not isinstance(questions_raw, list):
        questions_raw = []
    questions = [str(x).strip() for x in questions_raw if str(x).strip()][:3]

    if not script:
        raise ValueError("AI 未返回口播稿内容")
    if len(highlights) != 2:
        raise ValueError("AI 未返回 2 条亮点，请重试")
    if len(reflections) < 3:
        reflections = generate_finance_reflections(
            title_text=title, summary_text=summary_raw, script_text=script
        )
    if not questions:
        questions = generate_sharp_questions(
            title_text=title,
            summary_text=summary_raw,
            script_text=script,
            persona_key=question_persona,
        )

    return script, highlights, reflections, questions[:3]


def translate_script(script_text: str, target_language: str) -> str:
    text = script_text.strip()
    if not text:
        raise ValueError("口播稿不能为空")
    if not target_language.strip():
        raise ValueError("目标语言不能为空")

    # 中文原文无需翻译，直接返回。
    if target_language == "Chinese":
        return text

    client = _build_client()
    prompt = (
        "你是专业新闻口播翻译编辑。"
        f"请将输入口播稿准确翻译为 {target_language}。"
        "要求：1）严格忠实原文，不增删事实；2）数字、专有名词、时间保持准确；"
        "3）输出自然、可直接朗读的播报语言；4）只返回译文正文，不要解释、不要引号、不要标题。"
    )
    try:
        completion = _chat_completion_with_model_fallback(
            client,
            messages=[
                {"role": "system", "content": [{"type": "text", "text": prompt}]},
                {"role": "user", "content": [{"type": "text", "text": text}]},
            ],
            max_completion_tokens=1600,
            stream=False,
        )
        output = _completion_text(completion).strip()
    except Exception as exc:
        raise ValueError(f"AI 翻译失败: {exc}") from exc

    if not output:
        raise ValueError("AI 翻译结果为空")
    # 避免模型返回 markdown 代码块，影响数字人口播。
    output = output.replace("```", "").strip()
    return output


def translate_report_package(
    title_text: str, script_text: str, highlights: list[str], target_language: str
) -> tuple[str, str, list[str]]:
    title = title_text.strip()
    script = script_text.strip()
    hl = [str(x).strip() for x in highlights if str(x).strip()][:2]

    if not script:
        raise ValueError("口播稿不能为空")
    if not target_language.strip():
        raise ValueError("目标语言不能为空")

    if target_language == "Chinese":
        return title, script, hl

    extra_rules = ""
    if "Cantonese" in target_language:
        extra_rules = "若目标语言为粤语，必须使用口语化粤语表达并采用繁体中文书写，不要退化为普通话书面语。"

    client = _build_client()
    prompt = (
        "你是专业新闻翻译编辑。"
        f"请将输入内容翻译为 {target_language}，并严格返回 JSON。"
        "不得新增或遗漏事实。"
        f"{extra_rules}"
        '输出格式：{"title":"...","script":"...","highlights":["...","..."]}'
        "仅返回 JSON，不要任何额外文字。"
    )
    source_payload = {
        "title": title,
        "script": script,
        "highlights": hl,
    }
    try:
        completion = _chat_completion_with_model_fallback(
            client,
            messages=[
                {"role": "system", "content": [{"type": "text", "text": prompt}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(source_payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            max_completion_tokens=2200,
            stream=False,
        )
        content = _completion_text(completion)
        json_text = _extract_json_text(content)
        if not json_text:
            raise ValueError("AI 返回格式异常，未解析到 JSON")
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI 返回 JSON 解析失败: {exc}") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"AI 翻译失败: {exc}") from exc

    title_out = str(parsed.get("title", "")).replace("```", "").strip() or title
    script_out = str(parsed.get("script", "")).replace("```", "").strip()
    highlights_raw = parsed.get("highlights", [])
    if not isinstance(highlights_raw, list):
        highlights_raw = []
    highlights_out = [
        str(x).replace("```", "").strip() for x in highlights_raw if str(x).strip()
    ][:2]

    if not script_out:
        raise ValueError("AI 翻译结果为空")
    if not highlights_out:
        highlights_out = hl

    return title_out, script_out, highlights_out


def generate_reflection_qa(
    title_text: str, summary_text: str, script_text: str
) -> list[tuple[str, str]]:
    title = title_text.strip()
    summary = summary_text.strip()
    script = script_text.strip()
    source_text = script or summary
    if not source_text:
        raise ValueError("会议内容不能为空")

    client = _build_client()
    prompt = (
        "你是会议复盘教练。"
        "请基于输入会议内容给出 3 组高质量反思问答。"
        "问题要具体、可执行，回答要简洁有行动建议。"
        '严格返回 JSON：{"qa":[{"question":"...","answer":"..."},{"question":"...","answer":"..."},{"question":"...","answer":"..."}]}'
        "只返回 JSON，不要其他文字。"
    )
    user_payload = {
        "title": title,
        "summary": summary,
        "script": script,
    }
    try:
        completion = _chat_completion_with_model_fallback(
            client,
            messages=[
                {"role": "system", "content": [{"type": "text", "text": prompt}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(user_payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            max_completion_tokens=1600,
            stream=False,
        )
        content = _completion_text(completion)
        json_text = _extract_json_text(content)
        if not json_text:
            raise ValueError("AI 返回格式异常，未解析到 JSON")
        parsed = json.loads(json_text)
        qa_raw = parsed.get("qa", [])
        if not isinstance(qa_raw, list):
            qa_raw = []
        qa_items: list[tuple[str, str]] = []
        for row in qa_raw:
            if not isinstance(row, dict):
                continue
            q = str(row.get("question", "")).strip()
            a = str(row.get("answer", "")).strip()
            if q and a:
                qa_items.append((q, a))
        if len(qa_items) >= 2:
            return qa_items[:3]
    except Exception:
        # 回退：在无可用模型时给出可执行模板，避免流程阻断。
        pass

    sentences = _split_sentences(source_text)
    key_point = sentences[0] if sentences else "当前会议目标"
    fallback = [
        (
            "这次会议最核心的目标是否清晰且可量化？",
            f"建议围绕“{key_point}”补充可量化指标与截止时间。",
        ),
        (
            "执行过程中最大的风险点是什么？",
            "建议按优先级列出前三个风险，并明确责任人与缓解动作。",
        ),
        (
            "下一次会议前，最关键的一项行动是什么？",
            "建议确定一个可在本周完成的行动项，并在下次会议做结果复盘。",
        ),
    ]
    return fallback


def generate_meeting_chapters_from_transcript(
    title_text: str, transcript_text: str
) -> list[str]:
    title = title_text.strip()
    transcript = transcript_text.strip()
    if not transcript:
        return []

    # 限制输入长度，避免超长逐字稿导致超时。
    source = transcript[:12000]
    client = _build_client()
    prompt = (
        "你是会议纪要编辑。请根据逐字稿抽取“章节纪要”，输出 3 到 6 条。"
        "每条必须是完整句，聚焦一个阶段主题，避免口语和赘述。"
        '严格返回 JSON：{"chapters":["章节1","章节2","章节3"]}。'
        "只返回 JSON，不要其他文字。"
    )

    try:
        completion = _chat_completion_with_model_fallback(
            client,
            messages=[
                {"role": "system", "content": [{"type": "text", "text": prompt}]},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "title": title,
                                    "transcript": source,
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                },
            ],
            max_completion_tokens=1600,
            stream=False,
        )
        content = _completion_text(completion)
        json_text = _extract_json_text(content)
        if not json_text:
            raise ValueError("AI 返回格式异常，未解析到 JSON")
        parsed = json.loads(json_text)
        raw = parsed.get("chapters", [])
        if not isinstance(raw, list):
            raw = []
        chapters = [str(x).replace("```", "").strip() for x in raw if str(x).strip()]
        return chapters[:6]
    except Exception:
        # 回退：从逐字稿句子中提炼最多 4 条可读章节句。
        lines = _split_sentences(source)
        cleaned: list[str] = []
        seen: set[str] = set()
        for line in lines:
            if len(line) < 10:
                continue
            normalized = re.sub(r"\s+", " ", line).strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(normalized)
            if len(cleaned) >= 4:
                break
        return cleaned


# 进程内 TTS 缓存：key = (text_sha256, language_key)，最多缓存 128 条，避免重复调用 Azure。
_tts_cache: dict[tuple[str, str], str] = {}
_TTS_CACHE_MAX = 128


def _tts_cache_key(text: str, language_key: str) -> tuple[str, str]:
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return (sha, language_key)


def synthesize_script_audio_pcm_base64(
    script_text: str, language_key: str, language_label: str
) -> str:
    text = script_text.strip()
    if not text:
        raise ValueError("口播稿不能为空")

    cache_key = _tts_cache_key(text, language_key)
    if cache_key in _tts_cache:
        return _tts_cache[cache_key]

    # 优先使用 Azure Speech 服务（语种覆盖更好，尤其粤语）。
    if (settings.azure_speech_key or "").strip():
        result = _synthesize_with_azure_speech_service(
            script_text=text,
            language_key=language_key,
            language_label=language_label,
        )
        if len(_tts_cache) >= _TTS_CACHE_MAX:
            _tts_cache.pop(next(iter(_tts_cache)))
        _tts_cache[cache_key] = result
        return result

    # 回退：Azure OpenAI TTS 部署。
    deployment = (settings.azure_tts_deployment_name or "").strip()
    if not deployment:
        raise ValueError(
            "未配置 TTS：请设置 AZURE_SPEECH_KEY 或 AZURE_TTS_DEPLOYMENT_NAME"
        )
    client = _build_client()
    voice = (settings.azure_tts_default_voice or "alloy").strip() or "alloy"
    response = None
    try:
        response = client.audio.speech.create(
            model=deployment,
            voice=voice,
            input=text,
            response_format="pcm",
            timeout=settings.azure_request_timeout_sec,
        )
    except Exception as exc:
        raise ValueError(
            f"AI 语音合成失败({language_key}/{language_label}): {exc}"
        ) from exc
    audio_bytes = _response_to_bytes(response)
    if not audio_bytes:
        raise ValueError(f"AI 语音合成结果为空({language_key}/{language_label})")
    pcm_bytes = _extract_wav_pcm_data(audio_bytes)
    if not pcm_bytes:
        raise ValueError(f"AI 语音 PCM 提取失败({language_key}/{language_label})")
    result = base64.b64encode(pcm_bytes).decode("ascii")
    if len(_tts_cache) >= _TTS_CACHE_MAX:
        _tts_cache.pop(next(iter(_tts_cache)))
    _tts_cache[cache_key] = result
    return result
