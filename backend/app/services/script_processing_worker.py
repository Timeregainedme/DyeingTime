"""给 Celery worker 使用的同步任务执行服务。"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chains.agents import ElementExtractorAgent, ScriptDividerAgent
from app.chains.agents import (
    CharacterPortraitAnalysisAgent,
    ConsistencyCheckerAgent,
    CostumeInfoAnalysisAgent,
    PropInfoAnalysisAgent,
    SceneInfoAnalysisAgent,
    ScriptOptimizerAgent,
    ScriptSimplifierAgent,
)
from app.chains.agents.script_processing_agents import (
    ScriptConsistencyCheckResult,
    ScriptDivisionResult,
    ScriptOptimizationResult,
    ScriptSimplificationResult,
)
from app.core.db_sync import sync_session_maker
from app.models.studio_shots import Shot
from app.services.script_extraction_cache import (
    build_script_extract_cache_key,
    get_cached_script_extract,
    set_cached_script_extract,
)
from app.services.llm.runtime import (
    build_default_text_llm_sync,
    build_fallback_text_llm_sync,
)
from app.services.studio.script_division import write_division_result_to_chapter_sync
from app.services.studio.script_division_chunking import (
    DivideChunkError,
    DivideChunksFailed,
    ScriptChunk,
    merge_chunk_shots,
    split_script_for_division,
)
from app.services.studio.shot_extracted_candidates import (
    sync_from_extraction_draft_sync as sync_shot_extracted_candidates_from_draft_sync,
)
from app.services.studio.shot_extracted_dialogue_candidates import (
    sync_from_extraction_draft_sync as sync_shot_extracted_dialogue_candidates_from_draft_sync,
)
from app.services.studio.shot_semantic_defaults import apply_shot_semantic_defaults_from_draft_sync
from app.services.worker.task_executor import (
    AbstractLLMResultGenerator,
    AbstractWorkerTaskExecutor,
    WorkerTaskContext,
)


logger = logging.getLogger(__name__)

# 资产提取每批镜头数：单批太大时 LLM 容易漏镜/输出过长；太小则调用次数过多。
EXTRACT_BATCH_SIZE = 8
EXTRACT_BATCH_TIMEOUT_SECONDS = 180.0
EXTRACT_MAX_PARALLEL_BATCHES = 2


class DivideResultGenerator(AbstractLLMResultGenerator):
    """分镜切分：分块并行 + 主模型超时 + 备用模型降级。"""

    thinking = False
    # 单块单模型最多等 90 秒；超时后立刻切备用模型，避免整单干等几分钟。
    chunk_timeout_seconds = 90.0
    max_parallel_chunks = 3

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> ScriptDivisionResult:
        agent = ScriptDividerAgent(llm)
        return agent.divide_script(script_text=str(run_args.get("script_text") or ""))

    def _divide_chunk(
        self,
        chunk: ScriptChunk,
        primary_llm: Any,
        fallback_llm: Any,
    ) -> tuple[ScriptChunk, ScriptDivisionResult]:
        """单块优先主模型，失败后立刻用备用模型重试一次。"""
        try:
            return chunk, self.generate_with_llm(primary_llm, {"script_text": chunk.text})
        except Exception as primary_exc:  # noqa: BLE001 - 单块失败要转成可重试信息
            if fallback_llm is None:
                raise DivideChunkError(chunk.index, str(primary_exc)) from primary_exc
            try:
                return chunk, self.generate_with_llm(fallback_llm, {"script_text": chunk.text})
            except Exception as fallback_exc:  # noqa: BLE001
                raise DivideChunkError(
                    chunk.index,
                    f"主模型失败：{primary_exc}；备用模型失败：{fallback_exc}",
                ) from fallback_exc

    def generate(
        self,
        db: Session,
        run_args: dict[str, Any],
        *,
        progress_cb: Callable[[int], None] | None = None,
    ) -> ScriptDivisionResult:
        script_text = str(run_args.get("script_text") or "")
        chunks = split_script_for_division(script_text)
        if not chunks:
            raise ValueError("剧本文本为空，无法切分镜")

        primary_llm = build_default_text_llm_sync(
            db,
            thinking=self.thinking,
            timeout=self.chunk_timeout_seconds,
            max_retries=0,
        )
        fallback_llm = build_fallback_text_llm_sync(
            db,
            thinking=self.thinking,
            timeout=self.chunk_timeout_seconds,
            max_retries=0,
        )

        # 单块不必开线程池，直接走一次；仍然享受主/备模型降级。
        if len(chunks) == 1:
            if progress_cb:
                progress_cb(20)
            result = self._divide_chunk(chunks[0], primary_llm, fallback_llm)[1]
            if progress_cb:
                progress_cb(80)
            return result

        results: list[tuple[ScriptChunk, ScriptDivisionResult]] = []
        errors: list[DivideChunkError] = []
        workers = min(self.max_parallel_chunks, len(chunks))
        completed = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {
                pool.submit(self._divide_chunk, chunk, primary_llm, fallback_llm): chunk
                for chunk in chunks
            }
            for future in as_completed(future_map):
                try:
                    results.append(future.result())
                except DivideChunkError as exc:
                    errors.append(exc)
                except Exception as exc:  # noqa: BLE001 - 兜底，避免线程异常直接吞掉
                    errors.append(DivideChunkError(future_map[future].index, str(exc)))
                completed += 1
                if progress_cb:
                    progress_cb(10 + int(70 * completed / len(chunks)))

        if errors:
            raise DivideChunksFailed(sorted(errors, key=lambda item: item.chunk_index))

        results.sort(key=lambda item: item[0].index)
        merged = merge_chunk_shots(results)
        if merged.total_shots <= 0:
            raise ValueError("分块切分完成后没有任何镜头")
        if progress_cb:
            progress_cb(85)
        return merged


class ExtractResultGenerator(AbstractLLMResultGenerator):
    thinking = False

    def generate(
        self,
        db: Session,
        run_args: dict[str, Any],
        *,
        progress_cb: Callable[[int], None] | None = None,
    ) -> tuple[Any, bool]:
        return generate_extraction_result(
            db=db,
            project_id=str(run_args.get("project_id") or ""),
            chapter_id=str(run_args.get("chapter_id") or ""),
            script_division=dict(run_args.get("script_division") or {}),
            consistency=dict(run_args.get("consistency") or {}) if run_args.get("consistency") else None,
            refresh_cache=bool(run_args.get("refresh_cache")),
            progress_cb=progress_cb,
        )

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> Any:  # pragma: no cover - 不直接走这里
        raise NotImplementedError


class ConsistencyResultGenerator(AbstractLLMResultGenerator):
    thinking = True

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> ScriptConsistencyCheckResult:
        agent = ConsistencyCheckerAgent(llm)
        return agent.extract(script_text=str(run_args.get("script_text") or ""))


class CharacterPortraitResultGenerator(AbstractLLMResultGenerator):
    thinking = True

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> Any:
        agent = CharacterPortraitAnalysisAgent(llm)
        return agent.analyze_character_description(
            character_context=run_args.get("character_context"),
            character_description=str(run_args.get("character_description") or ""),
        )


class PropInfoResultGenerator(AbstractLLMResultGenerator):
    thinking = True

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> Any:
        agent = PropInfoAnalysisAgent(llm)
        return agent.analyze_prop_description(
            prop_context=run_args.get("prop_context"),
            prop_description=str(run_args.get("prop_description") or ""),
        )


class SceneInfoResultGenerator(AbstractLLMResultGenerator):
    thinking = True

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> Any:
        agent = SceneInfoAnalysisAgent(llm)
        return agent.analyze_scene_description(
            scene_context=run_args.get("scene_context"),
            scene_description=str(run_args.get("scene_description") or ""),
        )


class CostumeInfoResultGenerator(AbstractLLMResultGenerator):
    thinking = True

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> Any:
        agent = CostumeInfoAnalysisAgent(llm)
        return agent.analyze_costume_description(
            costume_context=run_args.get("costume_context"),
            costume_description=str(run_args.get("costume_description") or ""),
        )


class ScriptOptimizationResultGenerator(AbstractLLMResultGenerator):
    thinking = True

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> ScriptOptimizationResult:
        agent = ScriptOptimizerAgent(llm)
        return agent.extract(
            script_text=str(run_args.get("script_text") or ""),
            consistency_json=json.dumps(dict(run_args.get("consistency") or {}), ensure_ascii=False),
        )


class ScriptSimplificationResultGenerator(AbstractLLMResultGenerator):
    thinking = True

    def generate_with_llm(self, llm, run_args: dict[str, Any]) -> ScriptSimplificationResult:
        agent = ScriptSimplifierAgent(llm)
        return agent.extract(script_text=str(run_args.get("script_text") or ""))


class DivideTaskExecutor(AbstractWorkerTaskExecutor):
    task_kind = "script_divide"
    # 分块并行后正常 1–3 分钟完成；10 分钟仍未完成视为异常。
    timeout_seconds = 600.0

    def __init__(self) -> None:
        super().__init__(session_maker=sync_session_maker)
        self._generator = DivideResultGenerator()

    def execute(self, ctx: WorkerTaskContext, run_args: dict[str, Any]) -> ScriptDivisionResult:
        def progress(value: int) -> None:
            ctx.store.set_progress(ctx.task_id, value)
            ctx.db.commit()

        return self._generator.generate(ctx.db, run_args, progress_cb=progress)

    def should_apply(self, ctx: WorkerTaskContext, run_args: dict[str, Any], result: ScriptDivisionResult) -> bool:  # noqa: ARG002
        return bool(run_args.get("write_to_db"))

    def apply_result(self, ctx: WorkerTaskContext, run_args: dict[str, Any], result: ScriptDivisionResult) -> None:
        chapter_id = str(run_args.get("chapter_id") or "")
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required for write_to_db=true")
        apply_division_result(ctx.db, chapter_id=chapter_id, result=result)


class ExtractTaskExecutor(AbstractWorkerTaskExecutor):
    task_kind = "script_extract"
    timeout_seconds = 1800.0

    def __init__(self) -> None:
        super().__init__(session_maker=sync_session_maker)
        self._generator = ExtractResultGenerator()

    def execute(self, ctx: WorkerTaskContext, run_args: dict[str, Any]) -> tuple[Any, bool]:
        def progress(value: int) -> None:
            ctx.store.set_progress(ctx.task_id, value)
            ctx.db.commit()

        return self._generator.generate(ctx.db, run_args, progress_cb=progress)

    def serialize_result(self, result: tuple[Any, bool]) -> dict[str, Any]:
        draft, from_cache = result
        return {
            "draft": draft.model_dump(),
            "from_cache": from_cache,
        }

    def should_apply(self, ctx: WorkerTaskContext, run_args: dict[str, Any], result: tuple[Any, bool]) -> bool:  # noqa: ARG002
        return True

    def apply_result(self, ctx: WorkerTaskContext, run_args: dict[str, Any], result: tuple[Any, bool]) -> None:
        draft, _from_cache = result
        chapter_id = str(run_args.get("chapter_id") or "")
        apply_extraction_result(ctx.db, chapter_id=chapter_id, draft=draft)


class ConsistencyTaskExecutor(AbstractWorkerTaskExecutor):
    task_kind = "script_consistency"
    succeeded_progress = 100
    timeout_seconds = 900.0

    def __init__(self) -> None:
        super().__init__(session_maker=sync_session_maker)
        self._generator = ConsistencyResultGenerator()

    def execute(self, ctx: WorkerTaskContext, run_args: dict[str, Any]) -> ScriptConsistencyCheckResult:
        return self._generator.generate(ctx.db, run_args)


class _SimpleLLMTaskExecutor(AbstractWorkerTaskExecutor):
    succeeded_progress = 100
    timeout_seconds = 900.0
    generator_class: type[AbstractLLMResultGenerator]

    def __init__(self) -> None:
        super().__init__(session_maker=sync_session_maker)
        self._generator = self.generator_class()

    def execute(self, ctx: WorkerTaskContext, run_args: dict[str, Any]) -> Any:
        return self._generator.generate(ctx.db, run_args)


class CharacterPortraitTaskExecutor(_SimpleLLMTaskExecutor):
    task_kind = "script_character_portrait"
    generator_class = CharacterPortraitResultGenerator


class PropInfoTaskExecutor(_SimpleLLMTaskExecutor):
    task_kind = "script_prop_info"
    generator_class = PropInfoResultGenerator


class SceneInfoTaskExecutor(_SimpleLLMTaskExecutor):
    task_kind = "script_scene_info"
    generator_class = SceneInfoResultGenerator


class CostumeInfoTaskExecutor(_SimpleLLMTaskExecutor):
    task_kind = "script_costume_info"
    generator_class = CostumeInfoResultGenerator


class ScriptOptimizationTaskExecutor(_SimpleLLMTaskExecutor):
    task_kind = "script_optimize"
    generator_class = ScriptOptimizationResultGenerator


class ScriptSimplificationTaskExecutor(_SimpleLLMTaskExecutor):
    task_kind = "script_simplify"
    generator_class = ScriptSimplificationResultGenerator


def generate_division_result(
    *,
    db: Session,
    script_text: str,
) -> ScriptDivisionResult:
    llm = build_default_text_llm_sync(db, thinking=False)
    agent = ScriptDividerAgent(llm)
    return agent.divide_script(script_text=script_text)


def apply_division_result(
    db: Session,
    *,
    chapter_id: str,
    result: ScriptDivisionResult,
) -> None:
    write_division_result_to_chapter_sync(db, chapter_id=chapter_id, result=result)


def _rebuild_script_division_from_shots(db: Session, chapter_id: str) -> dict[str, Any]:
    """从库内分镜重建 script_division。

    做什么：按章节内 ``Shot.index`` 顺序，把已落库的分镜还原成 ``ScriptDivisionResult``
    形状的 dict（``shots`` + ``total_shots``），供 ``ElementExtractorAgent`` 提取使用。
    为什么存在：extract-async 契约允许调用方不传 ``script_division``（前端 ChapterPrep
    恒传 ``{}``）；若原样透传空输入，LLM 会拿到空分镜，候选与资产全为空。

    行号口径：库内不保存剧本原始行号，这里按摘录文本行数累加出**连续且 >= 1** 的
    ``start_line/end_line``，既满足 ``ShotDivision`` 的 ``ge=1`` 契约（评审 C-17），
    也保留「越靠后的分镜行号越大」的单调顺序；LLM 提取本身主要依赖 ``script_excerpt``。
    """

    shots = db.execute(
        select(Shot)
        .where(Shot.chapter_id == chapter_id, Shot.skip_extraction.is_(False))
        .order_by(Shot.index)
    ).scalars().all()
    if not shots:
        return {"shots": [], "total_shots": 0}
    division_shots: list[dict[str, Any]] = []
    next_line = 1
    for shot in shots:
        excerpt = shot.script_excerpt or ""
        # 摘录为空时至少占 1 行，避免出现 end_line < start_line 或 0 这种违反契约的行号
        line_count = max(1, len(excerpt.splitlines()))
        start_line = next_line
        end_line = start_line + line_count - 1
        next_line = end_line + 1
        division_shots.append(
            {
                "index": shot.index,
                "start_line": start_line,
                "end_line": end_line,
                "script_excerpt": excerpt,
                "shot_name": shot.title or "",
            }
        )
    return {"shots": division_shots, "total_shots": len(division_shots)}


def _merge_extraction_drafts(
    primary: Any,
    secondary: Any,
) -> Any:
    """把 secondary 的镜头与全局实体并入 primary（按 name / index 去重）。

    用途：当 LLM 首轮提取漏掉部分镜头时，对缺失镜头单独补跑一次，
    再把结果合并回来。全局实体必须一起合并，否则 shots 里引用的名字
    在 primary 的全局列表中找不到，候选写入时会被跳过。
    """
    def _merge_by_name(dst: list[Any], src: list[Any]) -> None:
        existing = {str(getattr(x, "name", "")).strip() for x in dst}
        for item in src:
            name = str(getattr(item, "name", "")).strip()
            if name and name not in existing:
                dst.append(item)
                existing.add(name)

    _merge_by_name(primary.characters, secondary.characters)
    _merge_by_name(primary.scenes, secondary.scenes)
    _merge_by_name(primary.props, secondary.props)
    _merge_by_name(primary.costumes, secondary.costumes)

    existing_indexes = {int(s.index) for s in primary.shots}
    for shot in secondary.shots:
        if int(shot.index) not in existing_indexes:
            primary.shots.append(shot)
            existing_indexes.add(int(shot.index))
    return primary


def generate_extraction_result(
    *,
    db: Session,
    project_id: str,
    chapter_id: str,
    script_division: dict[str, Any],
    consistency: dict[str, Any] | None,
    refresh_cache: bool,
    progress_cb: Callable[[int], None] | None = None,
) -> tuple[Any, bool]:
    # 前端契约：script_division 可为空对象（ChapterPrep 恒传 {}），此时服务端从库内分镜重建。
    # 判定用「字段是否存在」而非「shots 是否为真值」：显式传 shots=[] 是调用方的明确意图
    # （空分镜提取），不能静默回退到库内分镜 —— 否则用户刚切换剧本、库内还是旧分镜时，会
    # 基于旧分镜产出候选而没有任何日志或响应信号（评审 C-17）。回退时记日志，让「本次沿用
    # 库内分镜」这件事可被察觉。
    if "shots" not in script_division:
        script_division = _rebuild_script_division_from_shots(db, chapter_id)
        logger.info(
            "script_division.shots 字段缺失，本次沿用库内分镜重建后提取：chapter_id=%s shots=%d",
            chapter_id,
            len(script_division.get("shots") or []),
        )
    elif not script_division.get("shots"):
        logger.info(
            "script_division.shots 为显式空列表，按调用方意图执行空分镜提取（不回退库内分镜）：chapter_id=%s",
            chapter_id,
        )

    cache_key = build_script_extract_cache_key(
        project_id=project_id,
        chapter_id=chapter_id,
        script_division=script_division,
        consistency=consistency,
    )

    result = None
    from_cache = False
    if not refresh_cache:
        result = get_cached_script_extract(cache_key)
        from_cache = result is not None

    if result is None:
        division_shots = list(script_division.get("shots") or [])
        batches = [
            division_shots[index : index + EXTRACT_BATCH_SIZE]
            for index in range(0, len(division_shots), EXTRACT_BATCH_SIZE)
        ] or [[]]
        primary_llm = build_default_text_llm_sync(
            db,
            thinking=False,
            timeout=EXTRACT_BATCH_TIMEOUT_SECONDS,
            max_retries=0,
        )
        fallback_llm = build_fallback_text_llm_sync(
            db,
            thinking=False,
            timeout=EXTRACT_BATCH_TIMEOUT_SECONDS,
            max_retries=0,
        )

        def run_batch(batch_shots: list[dict[str, Any]]) -> Any:
            payload = {"shots": batch_shots, "total_shots": len(batch_shots)}
            try:
                return ElementExtractorAgent(primary_llm).extract(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    script_division_json=json.dumps(payload, ensure_ascii=False),
                    consistency_json=json.dumps(consistency or {}, ensure_ascii=False),
                )
            except Exception as primary_exc:  # noqa: BLE001 - 失败后切备用模型
                if fallback_llm is None:
                    raise
                logger.warning(
                    "资产提取单批失败，切备用模型重试：chapter_id=%s shots=%s error=%s",
                    chapter_id,
                    [item.get("index") for item in batch_shots],
                    primary_exc,
                )
                return ElementExtractorAgent(fallback_llm).extract(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    script_division_json=json.dumps(payload, ensure_ascii=False),
                    consistency_json=json.dumps(consistency or {}, ensure_ascii=False),
                )

        batch_errors: list[str] = []
        drafts: list[Any] = []
        if len(batches) == 1:
            drafts.append(run_batch(batches[0]))
            if progress_cb:
                progress_cb(60)
        else:
            completed = 0
            with ThreadPoolExecutor(max_workers=min(EXTRACT_MAX_PARALLEL_BATCHES, len(batches))) as pool:
                future_map = {pool.submit(run_batch, batch): batch for batch in batches}
                for future in as_completed(future_map):
                    try:
                        drafts.append(future.result())
                    except Exception as exc:  # noqa: BLE001 - 单批失败不阻断其他批次
                        indexes = [item.get("index") for item in future_map[future]]
                        batch_errors.append(f"镜头 {indexes}: {exc}")
                        logger.exception("资产提取批次失败：chapter_id=%s shots=%s", chapter_id, indexes)
                    completed += 1
                    if progress_cb:
                        progress_cb(10 + int(55 * completed / len(batches)))

        if not drafts:
            raise RuntimeError("资产提取全部批次失败：" + "；".join(batch_errors))

        result = drafts[0]
        for draft in drafts[1:]:
            result = _merge_extraction_drafts(result, draft)

        # --- 覆盖校验 ---
        # prompt 里已要求「shots.index 必须覆盖并对应输入分镜中的 index」，
        # 但实测 LLM 仍会偶发漏掉末尾镜头（现象：批量提取后某个镜头完全没有候选，
        # 必须再单独点一次「刷新并提取」才会出现）。
        # 这里做后置校验：缺哪个 index，就用只含这些镜头的 script_division 补跑一次。
        expected_indexes = {
            int(item["index"]) for item in division_shots if isinstance(item, dict) and "index" in item
        }
        got_indexes = {int(shot.index) for shot in result.shots}
        missing = sorted(expected_indexes - got_indexes)
        still_missing: list[int] = []
        if missing:
            logger.warning(
                "提取结果缺少镜头 index=%s（期望 %d 个，实际 %d 个），自动补提取一次",
                missing,
                len(expected_indexes),
                len(got_indexes),
            )
            retry_shots = [
                item
                for item in division_shots
                if isinstance(item, dict) and int(item.get("index", -1)) in missing
            ]
            try:
                retry_result = run_batch(retry_shots)
                result = _merge_extraction_drafts(result, retry_result)
                still_missing = sorted(expected_indexes - {int(shot.index) for shot in result.shots})
                if still_missing:
                    logger.error("补提取后仍缺少镜头 index=%s，需人工重试", still_missing)
                else:
                    logger.info("补提取成功，已补齐镜头 index=%s", missing)
            except Exception:  # noqa: BLE001 - 补提取失败不应让整个任务失败
                still_missing = missing
                logger.exception("补提取失败（缺少镜头 index=%s），保留首轮结果", missing)

        if progress_cb:
            progress_cb(85)
        # 只有全部批次成功且镜头覆盖完整时才写缓存；部分失败留待下次重试。
        if not batch_errors and not still_missing:
            set_cached_script_extract(cache_key, result)

    return result, from_cache


def apply_extraction_result(
    db: Session,
    *,
    chapter_id: str,
    draft: Any,
) -> None:
    """将提取草稿同步为候选与镜头语言默认值。"""

    sync_shot_extracted_candidates_from_draft_sync(db, chapter_id=chapter_id, draft=draft)
    sync_shot_extracted_dialogue_candidates_from_draft_sync(db, chapter_id=chapter_id, draft=draft)
    apply_shot_semantic_defaults_from_draft_sync(db, chapter_id=chapter_id, draft=draft)


def run_divide_task_sync(task_id: str) -> None:
    DivideTaskExecutor().run(task_id)


def run_extract_task_sync(task_id: str) -> None:
    ExtractTaskExecutor().run(task_id)


def run_consistency_task_sync(task_id: str) -> None:
    ConsistencyTaskExecutor().run(task_id)


def run_character_portrait_task_sync(task_id: str) -> None:
    CharacterPortraitTaskExecutor().run(task_id)


def run_prop_info_task_sync(task_id: str) -> None:
    PropInfoTaskExecutor().run(task_id)


def run_scene_info_task_sync(task_id: str) -> None:
    SceneInfoTaskExecutor().run(task_id)


def run_costume_info_task_sync(task_id: str) -> None:
    CostumeInfoTaskExecutor().run(task_id)


def run_script_optimization_task_sync(task_id: str) -> None:
    ScriptOptimizationTaskExecutor().run(task_id)


def run_script_simplification_task_sync(task_id: str) -> None:
    ScriptSimplificationTaskExecutor().run(task_id)
